from django.contrib import admin

from .models import ChecklistTemplate, Question, Section


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("code", "text", "evidence_hint", "requires_photo", "order")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "order")
    list_filter = ("template",)
    inlines = [QuestionInline]


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "is_active")
    list_filter = ("is_active",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "section", "text", "requires_photo")
    list_filter = ("section__template", "section")
    search_fields = ("code", "text")
