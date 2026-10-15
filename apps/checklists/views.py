from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.core.audit import Action, log_event
from apps.core.permissions import role_required

from .forms import QuestionForm, SectionForm
from .models import ChecklistTemplate, Question, Section


@login_required
def template_list(request):
    templates = ChecklistTemplate.objects.prefetch_related("sections__questions")
    user = request.user
    if not user.is_admin_role:
        if user.is_inventory_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.INVENTORY_TEAM)
        elif user.is_marketing_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM)
        elif user.is_vm_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.VM_TEAM)
        elif user.is_grocery_home:
            templates = templates.filter(audience=ChecklistTemplate.Audience.GROCERY_HOME)
        else:
            templates = templates.filter(audience=ChecklistTemplate.Audience.CLUSTER_MANAGER)
    return render(request, "checklists/template_list.html", {"templates": templates})


@login_required
def template_detail(request, pk):
    qs = ChecklistTemplate.objects.prefetch_related("sections__questions")
    user = request.user
    if not user.is_admin_role:
        if user.is_inventory_team:
            qs = qs.filter(audience=ChecklistTemplate.Audience.INVENTORY_TEAM)
        elif user.is_marketing_team:
            qs = qs.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM)
        elif user.is_vm_team:
            qs = qs.filter(audience=ChecklistTemplate.Audience.VM_TEAM)
        elif user.is_grocery_home:
            qs = qs.filter(audience=ChecklistTemplate.Audience.GROCERY_HOME)
        else:
            qs = qs.filter(audience=ChecklistTemplate.Audience.CLUSTER_MANAGER)
    template = get_object_or_404(qs, pk=pk)
    return render(
        request,
        "checklists/template_detail.html",
        {
            "template": template,
            "sections": template.sections.all(),
        },
    )


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
def section_create(request, template_pk):
    template = get_object_or_404(ChecklistTemplate, pk=template_pk)
    if request.method == "POST":
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.template = template
            section.save()
            log_event(request, Action.CHECKLIST_CHANGED, template, label=str(template),
                      details=f"Section added: {section.name}")
            messages.success(request, f"Section '{section.name}' added.")
            return redirect("checklists:template_detail", pk=template.pk)
    else:
        last_order = template.sections.order_by("-order").values_list("order", flat=True).first() or 0
        form = SectionForm(initial={"order": last_order + 1})
    return render(
        request,
        "checklists/section_form.html",
        {"form": form, "template": template, "title": f"Add Section to {template.name}"},
    )


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
@require_POST
def section_delete(request, pk):
    section = get_object_or_404(Section.objects.select_related("template"), pk=pk)
    template_pk = section.template_id
    section_name = section.name
    has_responses = Question.objects.filter(section=section, responses__isnull=False).exists()
    if has_responses:
        messages.error(
            request,
            f"Cannot delete section '{section_name}' because some questions have responses recorded in visits.",
        )
        return redirect("checklists:template_detail", pk=template_pk)
    try:
        section.delete()
        log_event(request, Action.CHECKLIST_CHANGED, section.template, label=str(section.template),
                  details=f"Section deleted: {section_name}")
        messages.success(request, f"Section '{section_name}' deleted.")
    except ProtectedError:
        messages.error(request, f"Cannot delete section '{section_name}' due to related records.")
    return redirect("checklists:template_detail", pk=template_pk)


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
def question_create(request, template_pk):
    template = get_object_or_404(ChecklistTemplate, pk=template_pk)
    section_id = request.GET.get("section")
    initial = {}
    if section_id:
        initial["section"] = section_id

    if request.method == "POST":
        form = QuestionForm(request.POST, template=template)
        if form.is_valid():
            question = form.save()
            log_event(request, Action.CHECKLIST_CHANGED, template, label=str(template),
                      details=f"Question added: {question.code} · {question.text[:120]}")
            messages.success(request, f"Question '{question.code}' added.")
            return redirect("checklists:template_detail", pk=template.pk)
    else:
        if section_id:
            last_order = Question.objects.filter(section_id=section_id).order_by("-order").values_list("order", flat=True).first() or 0
            initial["order"] = last_order + 1
        form = QuestionForm(template=template, initial=initial)

    return render(
        request,
        "checklists/question_form.html",
        {"form": form, "template": template, "title": f"Add Question to {template.name}"},
    )


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
def question_update(request, pk):
    question = get_object_or_404(Question.objects.select_related("section__template"), pk=pk)
    template = question.section.template
    if request.method == "POST":
        original = Question.objects.get(pk=question.pk)  # the form updates `question` in place while validating
        form = QuestionForm(request.POST, instance=question, template=template)
        if form.is_valid():
            changed = list(form.changed_data)
            form.save()
            if changed:
                log_event(request, Action.CHECKLIST_CHANGED, template, label=str(template),
                          details=f"Question edited: {question.code} ({', '.join(changed)})",
                          changes={f: [getattr(original, f, ""), getattr(question, f, "")] for f in changed})
            messages.success(request, f"Question '{question.code}' updated.")
            return redirect("checklists:template_detail", pk=template.pk)
    else:
        form = QuestionForm(instance=question, template=template)
    return render(
        request,
        "checklists/question_form.html",
        {"form": form, "template": template, "question": question, "title": f"Edit Question {question.code}"},
    )


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
@require_POST
def question_delete(request, pk):
    question = get_object_or_404(Question.objects.select_related("section__template"), pk=pk)
    template_pk = question.section.template_id
    code = question.code
    if hasattr(question, "responses") and question.responses.exists():
        messages.error(
            request,
            f"Cannot delete question '{code}' because it has {question.responses.count()} recorded visit response(s).",
        )
        return redirect("checklists:template_detail", pk=template_pk)
    try:
        question.delete()
        log_event(request, Action.CHECKLIST_CHANGED, question.section.template, label=str(question.section.template),
                  details=f"Question deleted: {code}")
        messages.success(request, f"Question '{code}' deleted.")
    except ProtectedError:
        messages.error(request, f"Cannot delete question '{code}' because it is referenced by existing visits.")
    return redirect("checklists:template_detail", pk=template_pk)
