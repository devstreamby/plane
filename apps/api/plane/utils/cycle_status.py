# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""One status definition for scheduled and manually managed cycles."""

from django.db import transaction
from django.db.models import Case, CharField, F, Q, Value, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError


def cycle_status_expression():
    now = timezone.now()
    return Case(
        When(start_date__isnull=True, end_date__isnull=True, then=F("manual_status")),
        When(Q(start_date__lte=now) & Q(end_date__gte=now), then=Value("CURRENT")),
        When(start_date__gt=now, then=Value("UPCOMING")),
        When(end_date__lt=now, then=Value("COMPLETED")),
        default=Value("DRAFT"),
        output_field=CharField(),
    )


def get_cycle_status(cycle):
    if cycle.start_date is None and cycle.end_date is None:
        return cycle.manual_status
    now = timezone.now()
    if cycle.start_date and cycle.end_date and cycle.start_date <= now <= cycle.end_date:
        return "CURRENT"
    if cycle.start_date and cycle.start_date > now:
        return "UPCOMING"
    if cycle.end_date and cycle.end_date < now:
        return "COMPLETED"
    return "DRAFT"


def validate_cycle_dates(instance, data):
    start = data.get("start_date", instance.start_date if instance else None)
    end = data.get("end_date", instance.end_date if instance else None)
    if (start is None) != (end is None):
        raise ValidationError("Both start date and end date are either required or are to be null")
    if start and end and start > end:
        raise ValidationError("Start date cannot exceed end date")
    if instance and instance.manual_status != "DRAFT" and (start is not None or end is not None):
        raise ValidationError("Dates cannot be added to a manually started or completed cycle")


@transaction.atomic
def transition_cycle(cycle, target, actor):
    # Serialize competing start/complete requests without locking aggregate queries.
    cycle = type(cycle).objects.select_for_update().get(pk=cycle.pk)
    if cycle.archived_at or cycle.start_date is not None or cycle.end_date is not None:
        raise ValidationError("Only unarchived cycles without dates can be started or completed manually")
    expected = {"CURRENT": "DRAFT", "COMPLETED": "CURRENT"}.get(target)
    if expected is None or cycle.manual_status != expected:
        raise ValidationError("Invalid cycle status transition")
    cycle.manual_status = target
    cycle.updated_by = actor
    cycle.save(update_fields=["manual_status", "updated_by", "updated_at"])
    return cycle
