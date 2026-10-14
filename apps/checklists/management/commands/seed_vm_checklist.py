"""Seed the VM (Visual Merchandising) Team Store Visit checklists.

Source documents (project root):
- VM_StoreVisitChecklist.docx            -> VM Team - VM Manager   (VMM-001 .. VMM-070)
- VM_Executive StoreVisitChecklist.docx  -> VM Team - VM Executive (VME-001 .. VME-072)

Both templates are seeded under Audience.VM_TEAM.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.checklists.models import ChecklistTemplate, Question, Section

# (section, code, check point, evidence hint, requires_photo)
VM_TEMPLATES_DATA = {
    "VM Team - VM Manager": {
        "prefix": "VMM",
        "description": "Retail visual merchandising audit, action tracker and closure review for VM Manager.",
        "items": [
            ('Store Exterior & Entrance', 'VMM-001', 'Store facade, fascia and brand identity are clean, visible and free from damage.', 'First customer impression and arrival zone', False),
            ('Store Exterior & Entrance', 'VMM-002', 'Entrance is clutter-free; promotional elements do not obstruct customer flow or safety access.', 'First customer impression and arrival zone', False),
            ('Store Exterior & Entrance', 'VMM-003', 'Entrance focal point communicates the current season, campaign or new arrival message.', 'First customer impression and arrival zone', False),
            ('Store Exterior & Entrance', 'VMM-004', 'Opening-hours, service and mandatory customer communication are neat and current.', 'First customer impression and arrival zone', False),
            ('Store Exterior & Entrance', 'VMM-005', 'Entrance lighting is fully operational and highlights key products / communication.', 'First customer impression and arrival zone', False),
            ('Store Exterior & Entrance', 'VMM-006', 'Door glass, mirrors, pedestal surfaces and entrance fixtures are clean and fingerprint-free.', 'First customer impression and arrival zone', False),
            ('Store Exterior & Entrance', 'VMM-007', 'External / entrance props, plants and décor are aligned, stable and in good condition.', 'First customer impression and arrival zone', False),
            ('Windows & Campaign Execution', 'VMM-008', 'Window concept matches the approved campaign / seasonal direction.', 'Window story, campaign accuracy and visual impact', False),
            ('Windows & Campaign Execution', 'VMM-009', 'Window is visually balanced with a clear hero product, focal point and hierarchy.', 'Window story, campaign accuracy and visual impact', False),
            ('Windows & Campaign Execution', 'VMM-010', 'Mannequin count, positioning, pose and spacing match the approved VM standard.', 'Window story, campaign accuracy and visual impact', False),
            ('Windows & Campaign Execution', 'VMM-011', 'Window merchandise is complete, steamed, tagged discreetly and free from defects.', 'Window story, campaign accuracy and visual impact', False),
            ('Windows & Campaign Execution', 'VMM-012', 'Graphics / vinyl / campaign signage are correctly sized, positioned and damage-free.', 'Window story, campaign accuracy and visual impact', False),
            ('Windows & Campaign Execution', 'VMM-013', 'Lighting is aimed correctly with no dark spots, glare or failed lamps.', 'Window story, campaign accuracy and visual impact', False),
            ('Windows & Campaign Execution', 'VMM-014', 'Window floor / backdrop / props are clean, stable and free from visible storage or wiring.', 'Window story, campaign accuracy and visual impact', False),
            ('Floor Zoning & Customer Journey', 'VMM-015', 'Department zoning and category adjacency follow the approved layout / commercial logic.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-016', 'Main aisle, secondary aisles and customer pathways are clear and visually inviting.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-017', 'New arrivals and key seasonal stories are positioned in high-visibility / high-traffic zones.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-018', 'Best sellers / key volume lines receive adequate facing and accessible stock presentation.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-019', 'Slow movers / ageing merchandise have an approved VM action and are not occupying prime space without purpose.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-020', 'Cross-merchandising creates complete looks or relevant product solutions without confusing category ownership.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-021', 'Focal points are visible from the customer approach direction and are not blocked by fixtures or signage.', 'Department layout, hot zones and commercial placement', False),
            ('Floor Zoning & Customer Journey', 'VMM-022', 'Empty spaces, overfilled zones and dead corners are corrected to maintain balanced merchandise density.', 'Department layout, hot zones and commercial placement', False),
            ('Merchandise Presentation', 'VMM-023', 'Merchandise is presented by a clear colour story / collection / theme.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-024', 'Size sequence and size availability are consistent and easy for customers to shop.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-025', 'Hanging garments face the same direction; hangers are consistent and correctly spaced.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-026', 'Folded merchandise is aligned, evenly stacked and maintained at the approved stack height.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-027', 'Products are steamed / pressed and free from dust, stains, loose threads and visible damage.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-028', 'Broken assortments, single pieces and incomplete colour runs are identified for action.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-029', 'Replenishment is maintained so customer-facing fixtures do not look empty during trading hours.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Merchandise Presentation', 'VMM-030', 'Products are not mixed across unrelated price points / stories unless part of an approved presentation.', 'Product standards, colour flow, size flow and replenishment', False),
            ('Mannequins, Forms & Styling', 'VMM-031', 'All mannequins / bust forms are clean, stable and free from chips, cracks or missing parts.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Mannequins, Forms & Styling', 'VMM-032', 'Outfits are seasonally relevant and aligned to the approved styling direction.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Mannequins, Forms & Styling', 'VMM-033', 'Mannequin styling includes complete looks where appropriate: layers, accessories and footwear.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Mannequins, Forms & Styling', 'VMM-034', 'Garments fit correctly on mannequins; pins / clips / tags are not visible to customers.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Mannequins, Forms & Styling', 'VMM-035', 'Mannequin colours and outfits support the nearby merchandise story and are shoppable from the adjacent fixture.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Mannequins, Forms & Styling', 'VMM-036', 'Mannequin positions do not obstruct aisles, emergency routes, mirrors or product access.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Mannequins, Forms & Styling', 'VMM-037', 'Styling is refreshed after sell-through; sold-out items are replaced promptly with an approved alternative.', 'Outfit quality, grooming and shop-the-look execution', False),
            ('Fixtures, Shelves & Capacity', 'VMM-038', 'Fixtures are aligned, level, stable and positioned according to the approved floor plan.', 'Fixture condition, density and presentation discipline', False),
            ('Fixtures, Shelves & Capacity', 'VMM-039', 'Fixture capacity is appropriate: no overcrowding, rail compression or excessive empty space.', 'Fixture condition, density and presentation discipline', False),
            ('Fixtures, Shelves & Capacity', 'VMM-040', 'Shelves / tables / rails are clean and free from tape residue, dust and damaged surfaces.', 'Fixture condition, density and presentation discipline', False),
            ('Fixtures, Shelves & Capacity', 'VMM-041', 'All display accessories, arms, shelves, hooks and holders are intact and safely installed.', 'Fixture condition, density and presentation discipline', False),
            ('Fixtures, Shelves & Capacity', 'VMM-042', 'Height lines and presentation levels are consistent across adjacent fixtures.', 'Fixture condition, density and presentation discipline', False),
            ('Fixtures, Shelves & Capacity', 'VMM-043', 'Unused fixtures / extra hardware / cartons are removed from customer-visible areas.', 'Fixture condition, density and presentation discipline', False),
            ('Signage, Pricing & Customer Communication', 'VMM-044', 'Price points are visible, accurate and placed next to the relevant merchandise.', 'Accuracy, consistency and readability', False),
            ('Signage, Pricing & Customer Communication', 'VMM-045', 'Offer / promotion communication matches the live commercial offer and validity period.', 'Accuracy, consistency and readability', False),
            ('Signage, Pricing & Customer Communication', 'VMM-046', 'No expired, duplicate, handwritten or conflicting customer-facing signage is displayed.', 'Accuracy, consistency and readability', False),
            ('Signage, Pricing & Customer Communication', 'VMM-047', 'Sign holders, frames, acrylics and clips are clean, straight and undamaged.', 'Accuracy, consistency and readability', False),
            ('Signage, Pricing & Customer Communication', 'VMM-048', 'Category / navigation signage is visible from normal customer approach points.', 'Accuracy, consistency and readability', False),
            ('Signage, Pricing & Customer Communication', 'VMM-049', 'New Arrival / Best Seller / Value / Service messages are used only where relevant and approved.', 'Accuracy, consistency and readability', False),
            ('Signage, Pricing & Customer Communication', 'VMM-050', 'Mandatory terms, conditions and exclusions are readable where required for promotional communication.', 'Accuracy, consistency and readability', False),
            ('Lighting, Ambience & Housekeeping', 'VMM-051', 'All VM / accent / track lights are operational and aimed at merchandise, focal points and signs.', 'Visual comfort and presentation environment', False),
            ('Lighting, Ambience & Housekeeping', 'VMM-052', 'Light colour / intensity is consistent within the zone; no obvious dark or overexposed areas.', 'Visual comfort and presentation environment', False),
            ('Lighting, Ambience & Housekeeping', 'VMM-053', 'Mirrors and glass are clean and positioned to support presentation without glare or obstruction.', 'Visual comfort and presentation environment', False),
            ('Lighting, Ambience & Housekeeping', 'VMM-054', 'Floor, ceiling, pillars and walls around displays are clean and free from temporary clutter.', 'Visual comfort and presentation environment', False),
            ('Lighting, Ambience & Housekeeping', 'VMM-055', 'Music, fragrance and ambient presentation are appropriate to store standards and do not overpower the shopping experience.', 'Visual comfort and presentation environment', False),
            ('Lighting, Ambience & Housekeeping', 'VMM-056', 'Fitting-room approach / waiting areas remain visually neat and aligned with the department standard.', 'Visual comfort and presentation environment', False),
            ('Promotion, Seasonal & Launch Readiness', 'VMM-057', 'Current campaign / festival / event is fully executed in all identified customer touchpoints.', 'Execution against the current commercial calendar', False),
            ('Promotion, Seasonal & Launch Readiness', 'VMM-058', 'Promotional stock is visible in the planned location with sufficient display quantity.', 'Execution against the current commercial calendar', False),
            ('Promotion, Seasonal & Launch Readiness', 'VMM-059', 'Hero products and key price points are clearly communicated without excessive sign clutter.', 'Execution against the current commercial calendar', False),
            ('Promotion, Seasonal & Launch Readiness', 'VMM-060', 'Launch / promo elements are installed on time and old campaign material is fully removed.', 'Execution against the current commercial calendar', False),
            ('Promotion, Seasonal & Launch Readiness', 'VMM-061', 'Store team understands the VM intent and can maintain the display during peak trading hours.', 'Execution against the current commercial calendar', False),
            ('Promotion, Seasonal & Launch Readiness', 'VMM-062', 'Photo evidence of key campaign zones is captured and shared as per VM reporting requirement.', 'Execution against the current commercial calendar', True),
            ('VM Backroom, Assets & Team Compliance', 'VMM-063', 'VM props, graphics, forms and reusable assets are stored safely, labelled and easy to retrieve.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-064', 'Damaged props / fixtures / mannequins are logged with repair or replacement action.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-065', 'Basic VM tool kit is available: tape, cutter, cable ties, pins, cleaning kit and approved display tools.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-066', 'No customer merchandise is being used as unsecured backroom props / storage support.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-067', 'Store VM / floor team has a clear daily maintenance routine for windows, mannequins, folds and signage.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-068', 'Previous VM visit actions have evidence of closure; repeated gaps are escalated to the responsible manager.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-069', 'Store team can identify the current campaign, key VM priorities and no-change / critical standards.', 'Sustainability of standards after the visit', False),
            ('VM Backroom, Assets & Team Compliance', 'VMM-070', 'Before / after photo references and action closures are filed for follow-up and audit trail.', 'Sustainability of standards after the visit', True),
        ],
    },
    "VM Team - VM Executive": {
        "prefix": "VME",
        "description": "Visual merchandising execution, store walk, gap closure and photo evidence checklist for VM Executive.",
        "items": [
            ('Store Exterior & Entrance', 'VME-001', 'Facade, entrance and brand/store name visibility are clean, unobstructed and properly lit.', 'First impression and customer entry', False),
            ('Store Exterior & Entrance', 'VME-002', 'Entry promotional communication is current, correctly positioned and free from damage.', 'First impression and customer entry', False),
            ('Store Exterior & Entrance', 'VME-003', 'Decompression/entrance zone is not overcrowded with fixtures, bins, cartons or excess POSM.', 'First impression and customer entry', False),
            ('Store Exterior & Entrance', 'VME-004', 'Entrance focal display is seasonally relevant and aligned to current campaign/theme.', 'First impression and customer entry', False),
            ('Store Exterior & Entrance', 'VME-005', 'Customer path from entrance is open; no fixture or display blocks movement or sightlines.', 'First impression and customer entry', False),
            ('Store Exterior & Entrance', 'VME-006', 'Entry mannequins / feature displays are fully styled, clean and price/communication ready.', 'First impression and customer entry', False),
            ('Windows, Mannequins & Styling', 'VME-007', 'Window/display concept matches approved seasonal or campaign direction.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-008', 'Mannequins are clean, undamaged and correctly positioned on bases/podiums.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-009', 'Mannequin outfits are complete: top, bottom, footwear/accessories where applicable.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-010', 'Garments on mannequins are steamed, pinned neatly and fit the body form correctly.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-011', 'Mannequin styling reflects current commercial focus, newness and key price points.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-012', 'Outfits use coordinated colours, layering and accessories; no random mismatched styling.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-013', 'Price/signage near mannequin or display is correct, visible and not handwritten unless approved.', 'Fashion presentation standards', False),
            ('Windows, Mannequins & Styling', 'VME-014', 'Window lighting is operational and focused on merchandise without dark spots or glare.', 'Fashion presentation standards', False),
            ('Floor Zoning & Customer Journey', 'VME-015', 'Department and category zoning follows approved floor layout / adjacency.', 'Layout, flow and focal points', False),
            ('Floor Zoning & Customer Journey', 'VME-016', 'New Arrival / Bestseller / Promotion / Occasion focal points are clearly identifiable.', 'Layout, flow and focal points', False),
            ('Floor Zoning & Customer Journey', 'VME-017', 'Aisles and circulation space are free from cartons, trolleys, ladders and overextended racks.', 'Layout, flow and focal points', False),
            ('Floor Zoning & Customer Journey', 'VME-018', 'Key sightlines from escalator/lift/entrance lead to strong displays or category statements.', 'Layout, flow and focal points', False),
            ('Floor Zoning & Customer Journey', 'VME-019', 'Feature tables, podiums and hot zones are refreshed with commercial priority merchandise.', 'Layout, flow and focal points', False),
            ('Floor Zoning & Customer Journey', 'VME-020', 'Slow/non-relevant product is not occupying prime VM space without approval.', 'Layout, flow and focal points', False),
            ('Merchandise Presentation', 'VME-021', 'All hanging garments face one direction and hangers are consistent by category/brand.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-022', 'Hanger size/type is appropriate; broken, mismatched or branded-conflict hangers are removed.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-023', 'Products are arranged in logical colour flow / colour blocking as per VM standard.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-024', 'Sizes are sequenced consistently and customers can easily identify available sizes.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-025', 'Folded merchandise is uniformly folded, aligned and maintained at approved stack height.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-026', 'Fixture density is balanced: not overfilled, not visibly empty and easy to shop.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-027', 'Product fronts, sleeves, collars, tags and packaging are properly aligned and customer facing.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-028', 'Merchandise is steamed/ironed; no visible wrinkles, dust, stains or damaged pieces on display.', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-029', 'Coordinate stories are created where relevant (top-bottom-accessory / family / occasion look).', 'Hanging, folding, colour, size and density', False),
            ('Merchandise Presentation', 'VME-030', 'Replenishment is completed from available stock so key display capacity is maintained.', 'Hanging, folding, colour, size and density', False),
            ('Fixtures & Display Standards', 'VME-031', 'Fixtures are aligned in straight lines and placed according to approved planogram/layout.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-032', 'Racks, shelves, tables, glass and mirrors are clean and free from tape residue or damage.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-033', 'Fixture height and product blocking do not obstruct important sightlines.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-034', 'Wall bays are balanced and aligned; shelves/arms are level and spacing is consistent.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-035', 'No empty hangrails, open cartons or unused VM props are visible to customers.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-036', 'Props, risers and podiums are stable, safe and used only where they enhance the display.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-037', 'Feature tables/podiums have a clear product story rather than mixed unrelated items.', 'Presentation quality and safety', False),
            ('Fixtures & Display Standards', 'VME-038', 'Electrical/display components used for VM are safely routed and do not create trip hazards.', 'Presentation quality and safety', False),
            ('Signage, Price Communication & POSM', 'VME-039', 'All promotional signage matches the live offer and approved artwork.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-040', 'Offer dates, discount wording, price points and exclusions are correct and readable.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-041', 'Old/expired campaign material, wobblers, tent cards and posters are fully removed.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-042', 'Category headers and navigation signage are visible, straight and clean.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-043', 'Price communication is placed consistently and does not cover product or brand identity.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-044', 'No unofficial handwritten signs / printouts are used without management approval.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-045', 'POSM quantity is controlled; area does not appear cluttered or over-communicated.', 'Accuracy and visual discipline', False),
            ('Signage, Price Communication & POSM', 'VME-046', 'Damaged, faded or low-quality printed material is replaced or reported for replacement.', 'Accuracy and visual discipline', False),
            ('Promotion / Campaign Execution', 'VME-047', 'Campaign execution matches approved reference images / VM guideline.', 'Launch readiness and consistency', False),
            ('Promotion / Campaign Execution', 'VME-048', 'All required campaign elements are installed in the correct locations.', 'Launch readiness and consistency', False),
            ('Promotion / Campaign Execution', 'VME-049', 'Offer merchandise is sufficiently available on floor and easy to identify.', 'Launch readiness and consistency', False),
            ('Promotion / Campaign Execution', 'VME-050', 'High-value campaign space is allocated to the intended category / product focus.', 'Launch readiness and consistency', False),
            ('Promotion / Campaign Execution', 'VME-051', 'Promotion fixture has clear entry price / hero price / offer message where required.', 'Launch readiness and consistency', False),
            ('Promotion / Campaign Execution', 'VME-052', 'Cross-merchandising supports the campaign without confusing the core offer.', 'Launch readiness and consistency', False),
            ('Promotion / Campaign Execution', 'VME-053', 'Before/after or completion photos are captured from standard angles for reporting.', 'Launch readiness and consistency', True),
            ('Promotion / Campaign Execution', 'VME-054', 'Any missing artwork, prop, fixture or stock dependency is reported with owner and ETA.', 'Launch readiness and consistency', False),
            ('Housekeeping & Ambience', 'VME-055', 'VM zones, shelves, tables, mirrors, podiums and mannequin bases are dust-free.', 'Visual cleanliness around merchandising', False),
            ('Housekeeping & Ambience', 'VME-056', 'No loose plastic, cartons, tagging waste, security pins or packaging is visible on floor.', 'Visual cleanliness around merchandising', False),
            ('Housekeeping & Ambience', 'VME-057', 'Lighting is working in VM focal points; fused lamps or dark zones are reported.', 'Visual cleanliness around merchandising', False),
            ('Housekeeping & Ambience', 'VME-058', 'Music, fragrance and general ambience do not interfere with product presentation.', 'Visual cleanliness around merchandising', False),
            ('Housekeeping & Ambience', 'VME-059', 'Fitting room approach and nearby display area are clean and visually maintained.', 'Visual cleanliness around merchandising', False),
            ('Housekeeping & Ambience', 'VME-060', 'Cash counter/queue area impulse displays are neat, relevant and not overstocked.', 'Visual cleanliness around merchandising', False),
            ('Stock Visibility & Commercial VM', 'VME-061', 'Key display styles have sufficient stock/size depth or a replacement style has been used.', 'Display linked to available stock', False),
            ('Stock Visibility & Commercial VM', 'VME-062', 'New arrivals are displayed promptly and are not held only in backroom / unopened cartons.', 'Display linked to available stock', False),
            ('Stock Visibility & Commercial VM', 'VME-063', 'Fast sellers and bestsellers are visibly represented in customer-facing zones.', 'Display linked to available stock', False),
            ('Stock Visibility & Commercial VM', 'VME-064', 'Empty display positions are refilled or remerchandised within the visit.', 'Display linked to available stock', False),
            ('Stock Visibility & Commercial VM', 'VME-065', 'Overstock is presented without compromising visual density and customer access.', 'Display linked to available stock', False),
            ('Stock Visibility & Commercial VM', 'VME-066', 'VM team flags stock gaps that are repeatedly weakening a planned story or campaign.', 'Display linked to available stock', False),
            ('VM Assets, Backroom & Team Discipline', 'VME-067', 'VM props, signage, acrylics, frames and reusable materials are stored safely and labelled.', 'Control and sustainability', False),
            ('VM Assets, Backroom & Team Discipline', 'VME-068', 'Old campaign material is segregated for reuse/disposal as instructed; floor is not used for storage.', 'Control and sustainability', False),
            ('VM Assets, Backroom & Team Discipline', 'VME-069', 'Steamer, ladder and VM tools are available, safe and returned to the designated place after use.', 'Control and sustainability', False),
            ('VM Assets, Backroom & Team Discipline', 'VME-070', 'Floor team understands the key VM standards they must maintain after the executive leaves.', 'Control and sustainability', False),
            ('VM Assets, Backroom & Team Discipline', 'VME-071', 'Corrected displays are handed over to Floor Manager / TL with clear maintenance instructions.', 'Control and sustainability', False),
            ('VM Assets, Backroom & Team Discipline', 'VME-072', 'All critical non-compliances are escalated on the same day with photos and required support.', 'Control and sustainability', True),
        ],
    },
}


class Command(BaseCommand):
    help = "Seed the VM Team store visit checklist templates (VM Manager & VM Executive)."

    @transaction.atomic
    def handle(self, *args, **options):
        total_questions = 0
        for template_name, data in VM_TEMPLATES_DATA.items():
            template, created = ChecklistTemplate.objects.get_or_create(
                name=template_name,
                version=1,
                defaults={
                    "is_active": True,
                    "description": data["description"],
                    "audience": ChecklistTemplate.Audience.VM_TEAM,
                },
            )
            if not created and template.audience != ChecklistTemplate.Audience.VM_TEAM:
                template.audience = ChecklistTemplate.Audience.VM_TEAM
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
                f"\nSuccessfully seeded {len(VM_TEMPLATES_DATA)} VM Team templates with {total_questions} total questions!"
            )
        )
