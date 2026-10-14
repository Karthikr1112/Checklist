"""Seed the Grocery & Home review checklists.

Source document (project root): "Grocery & Home CH & BH Store Visit Checklists.docx"
- Grocery & Home - Category Head - Grocery  (CHG-001 .. CHG-010)
- Grocery & Home - Category Head - Home     (CHH-001 .. CHH-010)
- Business Head, Grocery & Home           (BH-001 .. BH-010)

All templates are seeded under Audience.GROCERY_HOME. Template names end with the
user's Grocery & Home role so the Start Visit form can pick the right one.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.checklists.models import ChecklistTemplate, Question, Section

# (section, code, checkpoint, what to check, requires_photo)
GH_TEMPLATES_DATA = {
    "Grocery & Home - Category Head - Grocery": {
        "description": "Category Head, Grocery review. Covers FMCG (Non-Food and Food), Staples and Beverages.",
        "items": [
            ("Grocery Review", "CHG-001", "Budget vs achievement", "MTD by PGR and store, daily run-rate needed, and a dated recovery plan for the gap.", False),
            ("Grocery Review", "CHG-002", "Promo execution", "EC, FS and Bin placed per the HO plan in every store, with compliance % and photo proof. Promo price is in POS.", True),
            ("Grocery Review", "CHG-003", "Promo stock", "All promo SKUs are in stock and on display before the start date and through the promo.", False),
            ("Grocery Review", "CHG-004", "Core A-SKU availability", "Shelf matches system. Each missing A SKU has a PO or transfer, an expected date and a substitute.", False),
            ("Grocery Review", "CHG-005", "Stock days cover", "Cover against norm. A SKUs are not low, C SKUs are not high, and cover does not exceed shelf life.", False),
            ("Grocery Review", "CHG-006", "Dead and slow movers", "Stock aged >90 and >120 days has an exit route, owner and date. Re-ordering is blocked.", False),
            ("Grocery Review", "CHG-007", "Hygiene and FIFO/FEFO", "Sections are clean and damaged goods booked. Expiry register is signed, older batches are in front, and chiller and freezer temperatures are logged.", False),
            ("Grocery Review", "CHG-008", "Pending RTV", "RTVs older than 15 days have a debit note and pickup date. Credit notes are chased.", False),
            ("Grocery Review", "CHG-009", "Promoter roster and discipline", "Roster vs attendance, discipline lapses, and repeat cases escalated to the vendor.", False),
            ("Grocery Review", "CHG-010", "Gaps and action plan", "Every gap has a root cause, owner, due date and closure check. Anything open beyond 30 days is escalated.", False),
        ],
    },
    "Grocery & Home - Category Head - Home": {
        "description": "Category Head, Home review. Covers all Home categories.",
        "items": [
            ("Home Review", "CHH-001", "OPP price point availability", "The entry-price SKU is in stock and on shelf for every main and sub-category, in every store.", False),
            ("Home Review", "CHH-002", "Excess stock >30 days", "Listed by category, sub-category and store, with value.", False),
            ("Home Review", "CHH-003", "Liquidation or transfer plan", "Each excess item has a from-store, to-store, quantity, date and owner, or a markdown plan. Regular sellers at zero store stock while the warehouse has stock are cleared by transfer.", False),
            ("Home Review", "CHH-004", "Signage execution", "Category, price-point and promo signage is validated by photo or visit. Tags match system price and stale signage is removed.", True),
            ("Home Review", "CHH-005", "MTD budget vs achievement", "By store and category, with the run-rate needed to close.", False),
            ("Home Review", "CHH-006", "SM review", "Held with every store manager, with gap, reasons and commitments recorded. Last review's commitments are closed.", False),
            ("Home Review", "CHH-007", "Support required", "Stock, manpower, signage, price and marketing needs are logged with an owner and date.", False),
            ("Home Review", "CHH-008", "Promo execution", "Displays are as per the HO plan, stock is ready before start, and POS price is correct. Uplift vs baseline is reviewed.", False),
            ("Home Review", "CHH-009", "People support", "Staffing vs need, vacancies, product training (especially appliances), festive cover and vendor staff discipline.", False),
            ("Home Review", "CHH-010", "Gaps and action plan", "Each gap has a root cause, owner, due date and closure check. Items open beyond 30 days are escalated.", False),
        ],
    },
    "Business Head, Grocery & Home": {
        "description": "Business Head, Grocery & Home review. Exception-based: checks the category heads' outcomes and the decisions owed, not store-level detail.",
        "items": [
            ("Business Review", "BH-001", "Budget", "LOB: Grocery + Home. MTD vs achievement by LOB and store. Each category head's recovery plan has dates, and every laggard store has a named driver.", False),
            ("Business Review", "BH-002", "Margin", "LOB: Grocery + Home. Margin vs plan. Every negative-margin SKU has an owner and a fix date.", False),
            ("Business Review", "BH-003", "Promo", "LOB: Grocery. HO plan compliance (EC, FS, Bin) and promo stock readiness. Stores below standard are named.", False),
            ("Business Review", "BH-004", "Availability", "LOB: Grocery. A-SKU availability by store, with gaps split into PO needed and transfer needed.", False),
            ("Business Review", "BH-005", "OPP and signage", "LOB: Home. OPP price point availability and signage execution. Stores below standard are named.", False),
            ("Business Review", "BH-006", "Inventory health", "LOB: Grocery + Home. Grocery stock >90 and >120 days, Home stock >30 days, and value cleared vs plan. Markdowns waiting for approval are decided.", False),
            ("Business Review", "BH-007", "F&V dump and RTV", "LOB: Grocery. F&V dump % vs the 4% target, and RTV pending beyond 15 days including the DC. Worst stores and vendors are escalated.", False),
            ("Business Review", "BH-008", "Stock accuracy and store discipline", "LOB: Grocery + Home. Negative stock by store is corrected at source. Stores repeatedly failing hygiene, FIFO or signage have a support plan.", False),
            ("Business Review", "BH-009", "People", "LOB: Grocery + Home. Promoter discipline, Home staffing gaps, SM reviews done, and vendor escalations raised.", False),
            ("Business Review", "BH-010", "Governance", "LOB: Grocery + Home. Category head checklists submitted and scored. Actions open beyond 30 days are escalated, and pending decisions each have a deadline.", False),
        ],
    },
}


class Command(BaseCommand):
    help = "Seed the Grocery & Home review checklist templates (Category Head - Grocery / Home, Business Head, Grocery & Home)."

    @transaction.atomic
    def handle(self, *args, **options):
        total_questions = 0
        for template_name, data in GH_TEMPLATES_DATA.items():
            template, created = ChecklistTemplate.objects.get_or_create(
                name=template_name,
                version=1,
                defaults={
                    "is_active": True,
                    "description": data["description"],
                    "audience": ChecklistTemplate.Audience.GROCERY_HOME,
                },
            )
            if not created and template.audience != ChecklistTemplate.Audience.GROCERY_HOME:
                template.audience = ChecklistTemplate.Audience.GROCERY_HOME
                template.save(update_fields=["audience", "updated_at"])

            action_text = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action_text} template: {template_name}"))

            # Track section orders
            section_cache: dict[str, Section] = {}
            section_order: dict[str, int] = {}
            for item in data["items"]:
                sec_name = item[0]
                if sec_name not in section_order:
                    section_order[sec_name] = len(section_order) + 1

            for q_order, (sec_name, code, text, evidence, requires_photo) in enumerate(data["items"], start=1):
                section = section_cache.get(sec_name)
                if section is None:
                    section, _ = Section.objects.get_or_create(
                        template=template,
                        name=sec_name,
                        defaults={"order": section_order[sec_name]},
                    )
                    section_cache[sec_name] = section

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
                total_questions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully seeded {len(GH_TEMPLATES_DATA)} Grocery & Home templates with {total_questions} total questions!"
            )
        )
