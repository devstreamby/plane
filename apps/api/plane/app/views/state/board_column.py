# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import transaction
from django.db.utils import IntegrityError

# Third party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.serializers import BoardColumnSerializer
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import BoardColumn, State


class BoardColumnViewSet(BaseViewSet):
    """Board columns of a project.

    A column owns a set of states; a state belongs to at most one column and a
    state without a column is not mapped onto the board.
    """

    serializer_class = BoardColumnSerializer
    model = BoardColumn

    def get_queryset(self):
        return self.filter_queryset(
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(project_id=self.kwargs.get("project_id"))
            .filter(
                project__project_projectmember__member=self.request.user,
                project__project_projectmember__is_active=True,
                project__archived_at__isnull=True,
            )
            .prefetch_related("states")
            .distinct()
        )

    @staticmethod
    def _assign_states(project_id, column, state_ids):
        """Bulk-replace the states of a column.

        States listed here are moved into the column, states that were in it but
        are no longer listed are unmapped.
        """
        project_state_ids = {
            str(state_id) for state_id in State.objects.filter(project_id=project_id).values_list("id", flat=True)
        }
        for state_id in state_ids:
            if str(state_id) not in project_state_ids:
                return f"State {state_id} does not belong to this project"

        with transaction.atomic():
            State.objects.filter(project_id=project_id, board_column=column).exclude(id__in=state_ids).update(
                board_column=None
            )
            State.objects.filter(project_id=project_id, id__in=state_ids).update(board_column=column)
        return None

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def list(self, request, slug, project_id):
        return Response(
            BoardColumnSerializer(self.get_queryset(), many=True).data,
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id):
        try:
            serializer = BoardColumnSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(project_id=project_id)

            state_ids = request.data.get("state_ids")
            if isinstance(state_ids, list):
                error = self._assign_states(project_id, serializer.instance, state_ids)
                if error:
                    return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                BoardColumnSerializer(serializer.instance).data,
                status=status.HTTP_201_CREATED,
            )
        except IntegrityError as e:
            if "already exists" in str(e):
                return Response(
                    {"name": "The board column name is already taken"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, pk):
        try:
            column = BoardColumn.objects.get(pk=pk, project_id=project_id, workspace__slug=slug)

            state_ids = request.data.get("state_ids")
            if state_ids is not None and not isinstance(state_ids, list):
                return Response(
                    {"error": "state_ids must be a list of state ids"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = BoardColumnSerializer(column, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()

            if state_ids is not None:
                error = self._assign_states(project_id, column, state_ids)
                if error:
                    return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

            return Response(BoardColumnSerializer(column).data, status=status.HTTP_200_OK)
        except BoardColumn.DoesNotExist:
            return Response({"error": "Board column does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError as e:
            if "already exists" in str(e):
                return Response(
                    {"name": "The board column name is already taken"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, pk):
        column = BoardColumn.objects.filter(pk=pk, project_id=project_id, workspace__slug=slug).first()
        if column is None:
            return Response({"error": "Board column does not exist"}, status=status.HTTP_404_NOT_FOUND)
        # States keep existing, they just fall back to the unmapped group.
        State.objects.filter(project_id=project_id, board_column=column).update(board_column=None)
        column.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
