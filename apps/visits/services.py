"""Business logic for the Visit lifecycle."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.checklists.models import ChecklistTemplate
from apps.stores.models import Store

from .models import Response, Visit, VisitResponse, VisitStatus


@transaction.atomic
def start_visit(*, store: Store, template: ChecklistTemplate, cluster_manager, visit_date, audit_type) -> Visit:
    """Create a Visit and pre-create empty VisitResponse rows for every question."""
    visit = Visit.objects.create(
        store=store,
        template=template,
        cluster_manager=cluster_manager,
        visit_date=visit_date,
        audit_type=audit_type,
        status=VisitStatus.IN_PROGRESS,
    )
    questions = list(
        template.sections.prefetch_related("questions").values_list("questions__id", flat=True)
    )
    VisitResponse.objects.bulk_create(
        [VisitResponse(visit=visit, question_id=qid) for qid in questions if qid]
    )
    recompute_visit_metrics(visit)
    return visit


@transaction.atomic
def save_response(*, response: VisitResponse, value: str, evidence: dict, observation: str) -> VisitResponse:
    response.response = value
    response.evidence_data = evidence or {}
    response.observation = observation
    response.score = Decimal("1.00") if value == Response.YES else Decimal("0.00")
    response.save(update_fields=["response", "evidence_data", "observation", "score", "updated_at"])
    recompute_visit_metrics(response.visit)
    return response


def recompute_visit_metrics(visit: Visit) -> Visit:
    """Recalculate Yes/No/NA counts and compliance % per Excel scoring logic."""
    qs = visit.responses.all()
    total = qs.count()
    answered = qs.exclude(response="").count()
    yes_count = qs.filter(response=Response.YES).count()
    no_count = qs.filter(response=Response.NO).count()
    na_count = qs.filter(response=Response.NA).count()

    scoring_base = yes_count + no_count  # NA excluded
    pct = Decimal("0.00")
    if scoring_base:
        pct = (Decimal(yes_count) / Decimal(scoring_base) * Decimal("100")).quantize(Decimal("0.01"))

    Visit.objects.filter(pk=visit.pk).update(
        total_questions=total,
        answered_count=answered,
        yes_count=yes_count,
        no_count=no_count,
        na_count=na_count,
        compliance_pct=pct,
    )
    visit.refresh_from_db(fields=["total_questions", "answered_count", "yes_count", "no_count", "na_count", "compliance_pct"])
    return visit


@transaction.atomic
def submit_visit(visit: Visit) -> Visit:
    if visit.status not in {VisitStatus.DRAFT, VisitStatus.IN_PROGRESS, VisitStatus.FOLLOW_UP}:
        return visit
    visit.status = VisitStatus.SUBMITTED
    visit.submitted_at = timezone.now()
    visit.save(update_fields=["status", "submitted_at", "updated_at"])
    return visit


@transaction.atomic
def approve_visit(visit: Visit, approver) -> Visit:
    visit.status = VisitStatus.APPROVED
    visit.approved_at = timezone.now()
    visit.approved_by = approver
    visit.save(update_fields=["status", "approved_at", "approved_by", "updated_at"])
    return visit
