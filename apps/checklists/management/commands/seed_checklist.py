"""Seed the default Cluster Manager checklist (CM-001 .. CM-040)."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.checklists.models import ChecklistTemplate, Question, Section

TEMPLATE_NAME = "Cluster Manager Store Visit"
TEMPLATE_VERSION = 1

# (section, code, text, evidence_hint, requires_photo)
ITEMS: list[tuple[str, str, str, str, bool]] = [
    ("Sales", "CM-001", "Is Target vs Achievement reviewed for the store and all departments?", "MTD Ach % to be mentioned", False),
    ("Sales", "CM-002", "Is gap analysis conducted for underperformance?", "", False),
    ("Sales", "CM-003", "Is a clear action plan defined for improvement? (Dept by dept)", "", False),
    ("Margin", "CM-004", "Is FTD/MTD margin reviewed?", "Target Margin %; Actual Margin %", False),
    ("Margin", "CM-005", "Are margin improvement actions identified and tracked?", "", False),
    ("Inventory", "CM-006", "Is GRN closure completed as per P2P process?", "Pending Supplier GRN >24 Hrs; Pending WH GRNs >24 Hrs", False),
    ("Inventory", "CM-007", "Are dump & shrink monitored regularly?", "Dump %; Shrink %", False),
    ("Inventory", "CM-008", "Is SIT pending reviewed?", "", False),
    ("Inventory", "CM-009", "Are expiry and non-moving items tracked?", "Total Expiry Qty; Total Expiry Value", False),
    ("Inventory", "CM-010", "Is Shrinkage RCA and action plan implemented?", "", False),
    ("Inventory", "CM-011", "Is perpetual inventory / HV count conducted?", "Observations", False),
    ("Inventory", "CM-012", "Are RTV processes followed?", "", False),
    ("Inventory", "CM-013", "Is negative stock reviewed and corrected?", "Total Negative OH Items; Total Negative Stock Value", False),
    ("Manpower", "CM-014", "Is manpower as per plan vs actual reviewed?", "Mention key manpower gaps", False),
    ("Manpower", "CM-015", "Is attrition analyzed with reasons?", "", False),
    ("Manpower", "CM-016", "Is HR scorecard reviewed?", "", False),
    ("Housekeeping", "CM-017", "Is store cleanliness maintained?", "Front of Store; F&V section; Loose staples; Washrooms; Back Room", True),
    ("Housekeeping", "CM-018", "Is housekeeping manpower adequate?", "", False),
    ("Security", "CM-019", "Are security duties and posts reviewed?", "", False),
    ("Cash", "CM-020", "Is cash shortage/excess monitored and resolved?", "", False),
    ("Store Display", "CM-021", "Is the merchandise display neat and clean?", "", True),
    ("Store Display", "CM-022", "Is proper signage available?", "", True),
    ("Store Display", "CM-023", "Is price/size communication clear?", "", True),
    ("Store Display", "CM-024", "Are there any stocks in the floor without security tags? (Check 10 samples)", "Sample size: 10", False),
    ("SOP", "CM-025", "Is billing SOP followed correctly? (Observe 5 customer billings)", "Sample size: 5", False),
    ("Parking", "CM-026", "Is parking area clean and well managed?", "", True),
    ("Compliance", "CM-027", "Are all statutory licenses valid and available?", "", False),
    ("Compliance", "CM-028", "Are compliance issues identified and addressed?", "", False),
    ("Maintenance", "CM-029", "Are maintenance issues identified and resolved?", "", False),
    ("Fire Safety", "CM-030", "Are fire exits clear?", "", True),
    ("Fire Safety", "CM-031", "Is fire alarm system functional?", "", False),
    ("Fire Safety", "CM-032", "Is water pressure adequate?", "", False),
    ("Fire Safety", "CM-033", "Are staircases clear?", "", True),
    ("Backroom", "CM-034", "Is backroom organized and disciplined?", "", True),
    ("Returns", "CM-035", "Are returns being handed over to the respective department properly after tagging & barcoding?", "", False),
    ("Returns", "CM-036", "Are bills verified for all returns in the exchange register?", "", False),
    ("Finance", "CM-037", "Is petty cash audited monthly?", "Share results of last petty cash audit", False),
    ("Customer", "CM-038", "Is customer feedback reviewed and closed? (Feedback Register)", "", False),
    ("CCTV", "CM-039", "Is CCTV footage checked regularly?", "", False),
    ("Staff", "CM-040", "Is staff dining area clean?", "", True),
]


class Command(BaseCommand):
    help = "Seed the default Cluster Manager checklist template (CM-001..CM-040)."

    @transaction.atomic
    def handle(self, *args, **options):
        template, created = ChecklistTemplate.objects.get_or_create(
            name=TEMPLATE_NAME,
            version=TEMPLATE_VERSION,
            defaults={
                "is_active": True,
                "description": "Seeded from Cluster_Manager_Checklist_V1.xlsx",
                "audience": ChecklistTemplate.Audience.CLUSTER_MANAGER,
            },
        )
        if not created and template.audience != ChecklistTemplate.Audience.CLUSTER_MANAGER:
            template.audience = ChecklistTemplate.Audience.CLUSTER_MANAGER
            template.save(update_fields=["audience", "updated_at"])
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template {template}"))
        else:
            self.stdout.write(f"Template exists: {template} — syncing items.")

        # Preserve insertion order by section
        section_cache: dict[str, Section] = {}
        section_order: dict[str, int] = {}
        for section_name, *_ in ITEMS:
            if section_name not in section_order:
                section_order[section_name] = len(section_order) + 1

        for q_order, (section_name, code, text, evidence, requires_photo) in enumerate(ITEMS, start=1):
            section = section_cache.get(section_name)
            if section is None:
                section, _ = Section.objects.get_or_create(
                    template=template,
                    name=section_name,
                    defaults={"order": section_order[section_name]},
                )
                section_cache[section_name] = section

            Question.objects.update_or_create(
                section=section,
                code=code,
                defaults={
                    "text": text,
                    "evidence_hint": evidence,
                    "requires_photo": requires_photo,
                    "order": q_order,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(ITEMS)} questions across {len(section_cache)} sections."
            )
        )
