"""Seed the default Inventory Team daily checklist (IT-001 .. IT-037)."""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.checklists.models import ChecklistTemplate, Question, Section

TEMPLATE_NAME = "Inventory Team Daily Checklist"
TEMPLATE_VERSION = 1

# (section, code, text, evidence_hint, requires_photo)
ITEMS: list[tuple[str, str, str, str, bool]] = [
    ("Team Compliance", "IT-001", "Are all inventory team members wearing the required uniform and ID?", "Daily", False),
    ("Team Compliance", "IT-002", "Are all inventory team members complying with grooming standards?", "Daily", False),
    ("Team Compliance", "IT-003", "Is security frisking and personal bag checking completed for staff while going out?", "Daily", False),
    ("Team Compliance", "IT-004", "Are Fresh & Loose department staff wearing mandatory masks and gloves?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-005", "Is the Security Inward Register verified against GRNs daily?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-006", "Is the Security Outward Register verified against RTV/IST records daily?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-007", "Have inward dates been recorded on cartons to support FEFO/FIFO movement of goods?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-008", "Has the goods inwarding and handling process been correctly followed?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-009", "Has the Store Logistics Manager checked the MRP at the inward point?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-010", "Have discrepancy notes been prepared and shared with the vendor/warehouse team?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-011", "Have receiving discrepancies been addressed within 48 hours?", "Within 48 hours", False),
    ("Receiving, GRN & Stock Movement", "IT-012", "Has the pending GRN review been completed and cleared before EOD?", "Before EOD", False),
    ("Receiving, GRN & Stock Movement", "IT-013", "Has in-transit stock clearing been completed?", "Daily", False),
    ("Receiving, GRN & Stock Movement", "IT-014", "Are damaged or expired stocks kept in the designated area?", "Daily", True),
    ("Receiving, GRN & Stock Movement", "IT-015", "Has the DAD booking been approved by email by the Operations Head before system posting?", "Before posting", False),
    ("Receiving, GRN & Stock Movement", "IT-016", "Has disposal of RTV or damaged stock happened as per process?", "Daily", False),
    ("Fresh, Expiry, RTV & Damages", "IT-017", "Has the F&V dump been processed as per process?", "Daily", False),
    ("Fresh, Expiry, RTV & Damages", "IT-018", "Has expiry and near-expiry stock been cleared from the floor and moved to the designated area?", "Daily", True),
    ("Fresh, Expiry, RTV & Damages", "IT-019", "Has RTV of expiry stock been completed as per process?", "Daily", False),
    ("Customer Returns & Credit Notes", "IT-020", "Has all returned merchandise at CSD been handed over to the TL?", "Daily", False),
    ("Customer Returns & Credit Notes", "IT-021", "Is each credit note supported by a security gate pass?", "Daily", False),
    ("Customer Returns & Credit Notes", "IT-022", "Are expired credit notes older than 14 days honored only with CM approval?", "Daily", False),
    ("Customer Returns & Credit Notes", "IT-023", "Is the return details register updated?", "Daily", False),
    ("Customer Returns & Credit Notes", "IT-024", "Are reasons for customer returns captured correctly?", "Daily", False),
    ("Customer Returns & Credit Notes", "IT-025", "Have all manual credit notes issued been closed?", "Daily", False),
    ("Stock Counts & Variance Control", "IT-026", "Have negative stock issues been addressed with support from the store team?", "Daily", False),
    ("Stock Counts & Variance Control", "IT-027", "Has the high-value physical count been completed?", "Daily", False),
    ("Stock Counts & Variance Control", "IT-028", "Has the Global daily count been completed for selected items as per process?", "Daily", False),
    ("Audits & Store Controls", "IT-029", "Have POS, cycle count, barcode, tagging, and expiry audits been completed?", "Daily", False),
    ("Audits & Store Controls", "IT-030", "Was billing observed at POS for at least 10 bills, and was the cashier following the required process?", "Daily / Minimum 10 bills", False),
    ("Audits & Store Controls", "IT-031", "Were random floor checks completed for items without barcodes, and were observations recorded?", "Daily / Random audit", False),
    ("Audits & Store Controls", "IT-032", "Were random floor checks completed for items without security tags, and were observations recorded?", "Daily / Random audit", False),
    ("Audits & Store Controls", "IT-033", "Were random floor checks completed for items past the best-before date, and were observations recorded?", "Daily / Random audit", False),
    ("Audits & Store Controls", "IT-034", "Has the gate pass audit for NRGP and RGP been completed?", "Daily", False),
    ("Audits & Store Controls", "IT-035", "If any difference is found between month-end Main Cash/Petty Cash balances and AX/Float Cash balances, has Finance been informed by the SM or Head Cashier?", "Month-end", False),
    ("Audits & Store Controls", "IT-036", "Is a list of emergency numbers available?", "Daily", True),
    ("Audits & Store Controls", "IT-037", "Have POS, cycle count, barcode, tagging, and expiry audits been reviewed and closed?", "Daily", False),
]


class Command(BaseCommand):
    help = "Seed the default Inventory Team daily checklist template (IT-001..IT-037)."

    @transaction.atomic
    def handle(self, *args, **options):
        template, created = ChecklistTemplate.objects.get_or_create(
            name=TEMPLATE_NAME,
            version=TEMPLATE_VERSION,
            defaults={
                "is_active": True,
                "description": "Seeded from Inventory_Team_Daily_Checklist.xlsx",
                "audience": ChecklistTemplate.Audience.INVENTORY_TEAM,
            },
        )
        if not created and template.audience != ChecklistTemplate.Audience.INVENTORY_TEAM:
            template.audience = ChecklistTemplate.Audience.INVENTORY_TEAM
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
