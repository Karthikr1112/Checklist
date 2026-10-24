"""Seed the default Store Manager daily store walk checklist (SM-001 .. SM-030)."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.checklists.models import ChecklistTemplate, Question, Section

TEMPLATE_NAME = "Store Manager Daily Store Walk Checklist"
TEMPLATE_VERSION = 1

# (section, code, text, evidence_hint, requires_photo)
ITEMS: list[tuple[str, str, str, str, bool]] = [
    # Cleanliness & Hygiene
    (
        "Cleanliness & Hygiene",
        "SM-001",
        "Is store surrounding area clean & free of litter ?",
        "Daily",
        True,
    ),
    (
        "Cleanliness & Hygiene",
        "SM-002",
        "Is store front façade, entrance, trolleys & baskets, CSD counter clean ?",
        "Daily",
        True,
    ),
    (
        "Cleanliness & Hygiene",
        "SM-003",
        "Is store floor, walls, fixtures, cash counter & equipments clean ?",
        "Daily",
        True,
    ),
    (
        "Cleanliness & Hygiene",
        "SM-004",
        "Is store GR area clean and free of excess / damaged / expired merchandise ?",
        "Daily",
        False,
    ),
    (
        "Cleanliness & Hygiene",
        "SM-005",
        "Is the BOH clean and organised?",
        "Daily",
        True,
    ),
    (
        "Cleanliness & Hygiene",
        "SM-006",
        "Is store washrooms cleaned ?",
        "Daily",
        False,
    ),
    (
        "Cleanliness & Hygiene",
        "SM-007",
        "Is the dining area clean ?",
        "Daily",
        True,
    ),
    # Display / POG / Promotion Management
    (
        "Display / POG / Promotion Management",
        "SM-008",
        "Check the soh of core A skus as per the assortment fixed by category",
        "Daily",
        False,
    ),
    (
        "Display / POG / Promotion Management",
        "SM-009",
        "Is the F&v quality check been done and updated in portal",
        "Daily",
        False,
    ),
    (
        "Display / POG / Promotion Management",
        "SM-010",
        "Are all advertised / main promo stocks available at secondary assets as per the promo file",
        "Daily",
        False,
    ),
    (
        "Display / POG / Promotion Management",
        "SM-011",
        "Check F&V and Loose pricing signage vs POS(random 10 skus)",
        "Sample size: 10 random SKUs",
        True,
    ),
    (
        "Display / POG / Promotion Management",
        "SM-012",
        "Are daily indents submitted and receipt shortages followed up?",
        "Daily",
        False,
    ),
    (
        "Display / POG / Promotion Management",
        "SM-013",
        "Are all End Caps as per promo plan & promo offers clearly communicated ?",
        "Daily",
        True,
    ),
    # Customer Service & Front End
    (
        "Customer Service and Front End",
        "SM-014",
        "Are Customer suggestions / Compliants recorded and relevent action taken within agreed time ?",
        "Daily",
        False,
    ),
    (
        "Customer Service and Front End",
        "SM-015",
        "Is the recording sent from Ho playing correctly",
        "Daily",
        False,
    ),
    (
        "Customer Service and Front End",
        "SM-016",
        "Are all credit notes authorized (signed) & maintained with proper records ?",
        "Daily",
        False,
    ),
    (
        "Customer Service and Front End",
        "SM-017",
        "Is surprise float cash check done by the head cashier / Ops ASM ?",
        "Daily",
        False,
    ),
    # Store Administration
    (
        "Store Administration",
        "SM-018",
        "Is staff groomimg standards as per guidelines ?",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-019",
        "Staff roster reviewed and absentisim/leave updated in style hr",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-020",
        "Has Target Vs Achievement been reviewed and necessary action taken for the gaps",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-021",
        "Is the daily hourly walk-in updated in portal",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-022",
        "Are all GRNs done on daily basis for both DC & DSD deliveries ?",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-023",
        "Has pending rtv above 15 days been cleared.",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-024",
        "Is suffiecient consumable stock availble.",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-025",
        "Is dump been posted daily and updated in portal",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-026",
        "Are all equipments (chillers / freezers / AC / DG) functioning properly ?",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-027",
        "Are all fire exit clear of merchandise ?",
        "Daily",
        True,
    ),
    (
        "Store Administration",
        "SM-028",
        "Is staff purchase / cash / belongings declaration register maninatined ?",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-029",
        "Is security guards checking / stamping all the bills at the exit?",
        "Daily",
        False,
    ),
    (
        "Store Administration",
        "SM-030",
        "Does store imprest cash, safe balance & float tally as per records ?",
        "Daily",
        False,
    ),
]


class Command(BaseCommand):
    help = "Seed the default Store Manager daily store walk checklist template (SM-001..SM-030)."

    @transaction.atomic
    def handle(self, *args, **options):
        template, created = ChecklistTemplate.objects.get_or_create(
            name=TEMPLATE_NAME,
            version=TEMPLATE_VERSION,
            defaults={
                "is_active": True,
                "description": "Seeded from Sm checklist-RC.xlsx - Store Manager Daily Store Walk Checklist",
                "audience": ChecklistTemplate.Audience.STORE_MANAGER,
            },
        )
        if not created and template.audience != ChecklistTemplate.Audience.STORE_MANAGER:
            template.audience = ChecklistTemplate.Audience.STORE_MANAGER
            template.save(update_fields=["audience", "updated_at"])
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template {template}"))
        else:
            self.stdout.write(f"Template exists: {template} — syncing items.")

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
