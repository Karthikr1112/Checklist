from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Iterable

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from django.http import HttpResponse
from django.utils import timezone

from apps.schedule.models import PlanStatus, VisitPlan


HEADERS: list[tuple[str, int]] = [
    ("Planned Date", 14),
    ("Day of Week", 13),
    ("Start Time", 12),
    ("End Time", 12),
    ("Duration", 12),
    ("Status", 14),
    ("Audit Type", 16),
    ("Store Code", 13),
    ("Store Name", 28),
    ("City", 16),
    ("Region", 14),
    ("Assigned User", 22),
    ("Employee ID", 15),
    ("Primary Role", 18),
    ("Department Role", 22),
    ("Scheduled By", 22),
    ("Scheduled By Emp ID", 18),
    ("Scheduled By Role", 18),
    ("Checklist Template", 28),
    ("Checklist Audience", 18),
    ("Planning Notes", 32),
    ("Reason for Last Edit", 32),
    ("Schedule Created At", 18),
    ("Schedule Updated At", 18),
    ("Visit Conducted", 14),
    ("Visit Status", 14),
]

# Color fills for status badges in Excel
STATUS_STYLES = {
    PlanStatus.PLANNED: {
        "fill": PatternFill(start_color="E0E7FF", end_color="E0E7FF", fill_type="solid"),
        "font": Font(name="Calibri", size=10, bold=True, color="3730A3"),
    },
    PlanStatus.CHECKED_IN: {
        "fill": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),
        "font": Font(name="Calibri", size=10, bold=True, color="92400E"),
    },
    PlanStatus.COMPLETED: {
        "fill": PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"),
        "font": Font(name="Calibri", size=10, bold=True, color="065F46"),
    },
    PlanStatus.MISSED: {
        "fill": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
        "font": Font(name="Calibri", size=10, bold=True, color="991B1B"),
    },
    PlanStatus.CANCELLED: {
        "fill": PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid"),
        "font": Font(name="Calibri", size=10, bold=True, color="475569"),
    },
}


def extract_plan_row(plan: VisitPlan) -> list:
    """Extract a complete 40-column row with all details for a VisitPlan."""
    # Compute duration
    duration_str = ""
    if plan.start_time and plan.end_time:
        try:
            td = datetime.combine(date.min, plan.end_time) - datetime.combine(date.min, plan.start_time)
            total_mins = max(0, int(td.total_seconds() // 60))
            hours, mins = divmod(total_mins, 60)
            duration_str = f"{hours}h {mins:02d}m"
        except Exception:
            duration_str = ""

    cm = getattr(plan, "cluster_manager", None)
    creator = getattr(plan, "created_by", None)
    store = getattr(plan, "store", None)
    tmpl = getattr(plan, "template", None)
    visit = getattr(plan, "visit", None)

    dept_role = ""
    if cm:
        dept_role = (
            getattr(cm, "marketing_role", "")
            or getattr(cm, "vm_role", "")
            or getattr(cm, "gh_role", "")
            or ""
        )

    return [
        plan.planned_date.strftime("%d-%b-%Y") if plan.planned_date else "",
        plan.planned_date.strftime("%A") if plan.planned_date else "",
        plan.start_time.strftime("%H:%M") if plan.start_time else "",
        plan.end_time.strftime("%H:%M") if plan.end_time else "",
        duration_str,
        plan.get_status_display(),
        plan.get_audit_type_display(),
        store.code if store else "",
        store.name if store else "",
        getattr(store, "city", "") if store else "",
        getattr(store, "region", "") if store else "",
        cm.full_name if cm else "",
        getattr(cm, "employee_id", "") if cm else "",
        cm.get_role_display() if cm else "",
        dept_role,
        creator.full_name if creator else "",
        getattr(creator, "employee_id", "") if creator else "",
        creator.get_role_display() if creator else "",
        tmpl.name if tmpl else "Auto-matched by role",
        tmpl.get_audience_display() if tmpl else "",
        plan.notes or "",
        plan.edit_reason or "",
        plan.created_at.strftime("%d-%b-%Y %H:%M") if plan.created_at else "",
        plan.updated_at.strftime("%d-%b-%Y %H:%M") if plan.updated_at else "",
        "Yes" if visit else "No",
        visit.get_status_display() if visit else "",
    ]


def export_plans_to_csv(plans: Iterable[VisitPlan], filename: str = "Schedules_Export.csv") -> HttpResponse:
    """Generate a clean, UTF-8 encoded CSV file with BOM containing all schedule details."""
    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens it with proper character encoding
    output.write("\ufeff")

    writer = csv.writer(output)
    writer.writerow([h[0] for h in HEADERS])

    for plan in plans:
        writer.writerow(extract_plan_row(plan))

    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def export_plans_to_excel(
    plans: Iterable[VisitPlan],
    filename: str = "Schedules_Export.xlsx",
    filter_description: str = "All schedules",
) -> HttpResponse:
    """Generate a beautifully formatted Excel workbook with KPI metrics and all schedule information."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Schedules"
    ws.views.sheetView[0].showGridLines = True

    # Common styling objects
    title_font = Font(name="Calibri", size=16, bold=True, color="1E293B")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    card_label_font = Font(name="Calibri", size=9, bold=True, color="64748B")
    card_value_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10, color="1E293B")

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    even_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    odd_row_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    card_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    thin_border_side = Side(border_style="thin", color="E2E8F0")
    thin_border = Border(
        left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side
    )
    header_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=Side(border_style="medium", color="1E293B"),
        bottom=Side(border_style="medium", color="1E293B"),
    )

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_wrap_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # 1. Title & Subtitle
    ws.merge_cells("A1:N1")
    ws["A1"] = "STORE VISIT PLANNED SCHEDULES"
    ws["A1"].font = title_font
    ws["A1"].alignment = align_left
    ws.row_dimensions[1].height = 25

    generated_str = timezone.localtime(timezone.now()).strftime("%d-%b-%Y %H:%M")
    ws.merge_cells("A2:N2")
    ws["A2"] = f"Generated on: {generated_str}   |   Filter: {filter_description}"
    ws["A2"].font = subtitle_font
    ws["A2"].alignment = align_left
    ws.row_dimensions[2].height = 18

    # 2. Materialize rows and compute quick KPIs for planned schedules
    plan_list = list(plans)
    total_count = len(plan_list)
    unique_stores = len({p.store_id for p in plan_list if p.store_id})
    unique_users = len({p.cluster_manager_id for p in plan_list if p.cluster_manager_id})
    full_audits = sum(1 for p in plan_list if p.audit_type == "FULL")
    surprise_audits = sum(1 for p in plan_list if p.audit_type == "SURPRISE")
    other_audits = total_count - (full_audits + surprise_audits)

    # KPI summary cards in Rows 4 & 5
    kpi_cards = [
        ("TOTAL PLANNED", total_count, "B", "C"),
        ("STORES", unique_stores, "D", "E"),
        ("ASSIGNED USERS", unique_users, "F", "G"),
        ("FULL VISITS", full_audits, "H", "I"),
        ("SURPRISE AUDITS", surprise_audits, "J", "K"),
        ("REVISIT / MONTHLY", other_audits, "L", "M"),
    ]

    ws.row_dimensions[4].height = 14
    ws.row_dimensions[5].height = 20
    for title, val, start_col, end_col in kpi_cards:
        ws.merge_cells(f"{start_col}4:{end_col}4")
        lbl_cell = ws[f"{start_col}4"]
        lbl_cell.value = title
        lbl_cell.font = card_label_font
        lbl_cell.fill = card_fill
        lbl_cell.alignment = align_center

        ws.merge_cells(f"{start_col}5:{end_col}5")
        val_cell = ws[f"{start_col}5"]
        val_cell.value = val
        val_cell.font = card_value_font
        val_cell.fill = card_fill
        val_cell.alignment = align_center

        # Apply borders to card cells
        for col_char in (start_col, end_col):
            for r in (4, 5):
                ws[f"{col_char}{r}"].border = thin_border

    # 3. Table Header Row (Row 7)
    header_row_idx = 7
    ws.row_dimensions[header_row_idx].height = 26
    for col_idx, (col_name, _) in enumerate(HEADERS, start=1):
        cell = ws.cell(row=header_row_idx, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = header_border
        cell.alignment = align_center

    # 4. Data Rows (Row 8 onwards)
    center_col_indices = {1, 2, 3, 4, 5, 6, 7, 8, 13, 17, 23, 24, 25, 26}
    wrap_col_indices = {9, 21, 22}

    current_row_idx = header_row_idx + 1
    for i, plan in enumerate(plan_list):
        row_data = extract_plan_row(plan)
        row_fill = odd_row_fill if i % 2 == 1 else even_row_fill
        ws.row_dimensions[current_row_idx].height = 20

        for col_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=current_row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = thin_border
            cell.fill = row_fill

            # Check if this is the Status column (column 6)
            if col_idx == 6 and plan.status in STATUS_STYLES:
                st = STATUS_STYLES[plan.status]
                cell.fill = st["fill"]
                cell.font = st["font"]
                cell.alignment = align_center
            elif col_idx in center_col_indices:
                cell.alignment = align_center
            elif col_idx in wrap_col_indices:
                cell.alignment = align_wrap_left
            else:
                cell.alignment = align_left

        current_row_idx += 1

    last_data_row = max(current_row_idx - 1, header_row_idx)

    # 5. Set column widths
    for col_idx, (_, default_width) in enumerate(HEADERS, start=1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = default_width

    # 6. Enable Auto-filter on the data table
    last_col_letter = get_column_letter(len(HEADERS))
    ws.auto_filter.ref = f"A{header_row_idx}:{last_col_letter}{last_data_row}"

    # 7. Freeze panes at Row 8
    ws.freeze_panes = "A8"

    # Save to memory stream
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)

    response = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
