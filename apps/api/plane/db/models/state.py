# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models
from django.template.defaultfilters import slugify
from django.db.models import Q

# Module imports
from .project import ProjectBaseModel
from plane.db.mixins import SoftDeletionManager

class StateGroup(models.TextChoices):
    BACKLOG = "backlog", "Backlog"
    UNSTARTED = "unstarted", "Unstarted"
    STARTED = "started", "Started"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    TRIAGE = "triage", "Triage"


# Default states
DEFAULT_STATES = [
    {
        "name": "Backlog",
        "color": "#60646C",
        "sequence": 15000,
        "group": StateGroup.BACKLOG.value,
        "default": True,
    },
    {
        "name": "Todo",
        "color": "#60646C",
        "sequence": 25000,
        "group": StateGroup.UNSTARTED.value,
    },
    {
        "name": "In Progress",
        "color": "#F59E0B",
        "sequence": 35000,
        "group": StateGroup.STARTED.value,
    },
    {
        "name": "Done",
        "color": "#46A758",
        "sequence": 45000,
        "group": StateGroup.COMPLETED.value,
    },
    {
        "name": "Cancelled",
        "color": "#9AA4BC",
        "sequence": 55000,
        "group": StateGroup.CANCELLED.value,
    },
    {
        "name": "Triage",
        "color": "#4E5355",
        "sequence": 65000,
        "group": StateGroup.TRIAGE.value,
    },
]


class StateManager(SoftDeletionManager):
    """Default manager - excludes triage states"""

    def get_queryset(self):
        return super().get_queryset().exclude(group=StateGroup.TRIAGE.value)


class TriageStateManager(SoftDeletionManager):
    """Manager for triage states only"""

    def get_queryset(self):
        return super().get_queryset().filter(group=StateGroup.TRIAGE.value)


class BoardColumn(ProjectBaseModel):
    """A column of the project's board.

    Columns are ordered by `sequence` and own a set of states: every state
    points at the column it is displayed in, and a state without a column is
    simply not mapped onto the board.
    """

    name = models.CharField(max_length=255, verbose_name="Board Column Name")
    sequence = models.FloatField(default=65535)

    def __str__(self):
        return f"{self.name} <{self.project.name}>"

    class Meta:
        unique_together = ["name", "project", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "project"],
                condition=Q(deleted_at__isnull=True),
                name="board_column_unique_name_project_when_deleted_at_null",
            )
        ]
        verbose_name = "Board Column"
        verbose_name_plural = "Board Columns"
        db_table = "board_columns"
        ordering = ("sequence",)

    def save(self, *args, **kwargs):
        if self._state.adding:
            last_sequence = BoardColumn.objects.filter(project=self.project).aggregate(
                largest=models.Max("sequence")
            )["largest"]
            if last_sequence is not None:
                self.sequence = last_sequence + 15000
        return super().save(*args, **kwargs)


class State(ProjectBaseModel):
    name = models.CharField(max_length=255, verbose_name="State Name")
    description = models.TextField(verbose_name="State Description", blank=True)
    color = models.CharField(max_length=255, verbose_name="State Color")
    slug = models.SlugField(max_length=100, blank=True)
    sequence = models.FloatField(default=65535)
    group = models.CharField(
        choices=StateGroup.choices,
        default=StateGroup.BACKLOG,
        max_length=20,
    )
    is_triage = models.BooleanField(default=False)
    default = models.BooleanField(default=False)
    # Workflow: when True, any state may transition into this one regardless of
    # the source state's configured outgoing transitions.
    allow_any_transition = models.BooleanField(default=False)
    # Board: the column this state is displayed in. Null means the state is not
    # mapped onto the board and falls into the "None" group.
    board_column = models.ForeignKey(
        BoardColumn,
        on_delete=models.SET_NULL,
        related_name="states",
        null=True,
        blank=True,
    )
    external_source = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, blank=True, null=True)

    objects = StateManager()
    all_state_objects = models.Manager()
    triage_objects = TriageStateManager()

    def __str__(self):
        """Return name of the state"""
        return f"{self.name} <{self.project.name}>"

    class Meta:
        unique_together = ["name", "project", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "project"],
                condition=Q(deleted_at__isnull=True),
                name="state_unique_name_project_when_deleted_at_null",
            )
        ]
        verbose_name = "State"
        verbose_name_plural = "States"
        db_table = "states"
        ordering = ("sequence",)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        if self._state.adding:
            # Get the maximum sequence value from the database
            last_id = State.objects.filter(project=self.project).aggregate(largest=models.Max("sequence"))["largest"]
            # if last_id is not None
            if last_id is not None:
                self.sequence = last_id + 15000

        return super().save(*args, **kwargs)


class StateTransition(ProjectBaseModel):
    """An allowed workflow transition between two states of the same project.

    Semantics: a state with no outgoing StateTransition rows allows transitions
    to every state; a state with one or more rows allows only the listed targets.
    """

    from_state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="transitions_from",
    )
    to_state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="transitions_to",
    )

    def __str__(self):
        return f"{self.from_state.name} -> {self.to_state.name} <{self.project.name}>"

    class Meta:
        unique_together = ["from_state", "to_state", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_state", "to_state"],
                condition=Q(deleted_at__isnull=True),
                name="state_transition_unique_from_to_when_deleted_at_null",
            )
        ]
        verbose_name = "State Transition"
        verbose_name_plural = "State Transitions"
        db_table = "state_transitions"
        ordering = ("created_at",)
