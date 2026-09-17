
import json

from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Category,
    Location,
    SpecificationDefinition,
    Personnel,
    Unit,
    Requester,
    Asset,
    AssetSpecification,
    Request,
    RequestHandling,
    Contract,
)


class AssetSelect(forms.Select):

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        if value:
            asset = value.instance

            if asset:
                option["attrs"]["data-warranty-status"] = (
                    asset.warranty_status
                )

        return option


class RequestHandlingForm(forms.ModelForm):

    warranty_status = forms.CharField(
        label="Warranty Status",
        required=False,
        widget=forms.TextInput(attrs={
            "readonly": "readonly",
        })
    )

    class Meta:
        model = RequestHandling
        fields = [
            "request",
            "asset",
            "warranty_status",
            "technician",
            "handled_date",
            "repair_location",
            "repair_performed_by",
            "repair_result",
            "next_action",
            "workshop_result",
            "external_approval",
            "external_repair_result",
            "replacement_asset",
            "replacement_type",
            "result",
        ]
        widgets = {
            "asset": AssetSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["external_approval"].required = False
        self.fields["next_action"].required = False

        if self.instance and self.instance.asset:
            self.fields["warranty_status"].initial = (
                self.instance.asset.warranty_status
            )

    def clean(self):
        cleaned_data = super().clean()

        asset = cleaned_data.get("asset")

        if asset:
            self.fields["warranty_status"].initial = (
                asset.warranty_status
            )

        if not cleaned_data.get("external_approval"):
            cleaned_data["external_approval"] = "NOT_REQUIRED"

        if not cleaned_data.get("next_action"):
            cleaned_data["next_action"] = "NONE"

        if (
            cleaned_data.get("external_repair_result") == "PAID_REPAIR"
            and cleaned_data.get("external_approval") != "APPROVED"
        ):
            self.add_error(
                "external_approval",
                "Paid External Repair requires Principal Approval."
            )

        if (
            cleaned_data.get("next_action") == "REPLACEMENT"
            and not cleaned_data.get("replacement_asset")
        ):
            self.add_error(
                "replacement_asset",
                "Replacement Asset is required for Replacement."
            )

        return cleaned_data


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location_type",
        "parent",
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    list_filter = (
        "location_type",
        "is_active",
    )


@admin.register(SpecificationDefinition)
class SpecificationDefinitionAdmin(admin.ModelAdmin):
    list_display = ("category", "name", "is_active")
    search_fields = ("name",)
    list_filter = ("category", "is_active")


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "phone", "is_active")
    search_fields = ("name", "position")
    list_filter = ("is_active",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Requester)
class RequesterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "unit",
        "phone",
        "email",
        "is_active",
    )

    search_fields = (
        "name",
        "user__username",
        "unit__name",
        "phone",
        "email",
    )

    list_filter = (
        "unit",
        "is_active",
    )


class AssetRequestHandlingInline(admin.TabularInline):
    model = RequestHandling
    fk_name = "asset"
    extra = 0
    fields = (
        "request",
        "technician",
        "handled_date",
        "repair_location",
        "repair_performed_by",
        "repair_result",
        "next_action",
    )
    readonly_fields = (
        "request",
        "technician",
        "handled_date",
        "repair_location",
        "repair_performed_by",
        "repair_result",
        "next_action",
    )


class AssetReplacementHistoryInline(admin.TabularInline):
    model = RequestHandling
    fk_name = "replacement_asset"
    extra = 0
    fields = (
        "request",
        "asset",
        "replacement_type",
        "technician",
        "handled_date",
    )
    readonly_fields = (
        "request",
        "asset",
        "replacement_type",
        "technician",
        "handled_date",
    )


class AssetSpecificationInline(admin.TabularInline):
    model = AssetSpecification
    extra = 1
    can_delete = True
    show_change_link = False
    verbose_name = "Asset Specification"
    verbose_name_plural = "Asset Specifications"
    fields = (
        "definition",
        "value",
    )

    def get_formset(self, request, obj=None, **kwargs):

        parent_category = None

        if obj and obj.category:
            parent_category = obj.category

        base_formset = super().get_formset(
            request,
            obj,
            **kwargs
        )

        class FilteredSpecificationForm(base_formset.form):

            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)

                self.fields["definition"].widget = forms.Select()

                if parent_category:
                    self.fields["definition"].queryset = (
                        SpecificationDefinition.objects.filter(
                            category=parent_category,
                            is_active=True,
                        )
                    )
                else:
                    self.fields["definition"].queryset = (
                        SpecificationDefinition.objects.none()
                    )

        class SpecificationFormSet(base_formset):

            def clean(self):
                super().clean()

                definitions = set()

                for form in self.forms:
                    if not hasattr(form, "cleaned_data"):
                        continue

                    if not form.cleaned_data:
                        continue

                    if form.cleaned_data.get("DELETE"):
                        continue

                    definition = form.cleaned_data.get("definition")

                    if not definition:
                        continue

                    if definition.pk in definitions:
                        raise ValidationError(
                            "The same specification cannot be added more than once to the same asset."
                        )

                    definitions.add(definition.pk)

                    if self.instance and self.instance.pk:
                        existing = AssetSpecification.objects.filter(
                            asset=self.instance,
                            definition=definition,
                        )

                        if form.instance and form.instance.pk:
                            existing = existing.exclude(
                                pk=form.instance.pk
                            )

                        if existing.exists():
                            raise ValidationError(
                                "The same specification already exists for this asset."
                            )

        SpecificationFormSet.form = FilteredSpecificationForm

        return SpecificationFormSet


class AssetCategorySelect(forms.Select):

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        if value:
            definitions = SpecificationDefinition.objects.filter(
                category_id=value,
                is_active=True,
            ).values("id", "name")

            option["attrs"]["data-specifications"] = json.dumps(
                list(definitions)
            )

        return option


class AssetForm(forms.ModelForm):

    class Meta:
        model = Asset
        fields = "__all__"
        widgets = {
            "category": AssetCategorySelect(),
        }

    def clean_category(self):
        category = self.cleaned_data.get("category")

        if self.instance and self.instance.pk:
            if category != self.instance.category:
                raise ValidationError(
                    "Asset Category cannot be changed after the Asset has been created. "
                    "Please create a new Asset with the correct Category."
                )

        return category


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):

    form = AssetForm

    inlines = [
        AssetRequestHandlingInline,
        AssetReplacementHistoryInline,
        AssetSpecificationInline,
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("category",)

        return ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "category" in form.base_fields:
            form.base_fields["category"].widget.attrs[
                "data-specification-url"
            ] = "/admin/core/specificationdefinition/"

        return form

    list_display = (
        "asset_id",
        "name",
        "category",
        "status",
        "location",
        "used_in",
        "warranty_expiry",
        "warranty_status",
        "warranty_alert",
    )

    search_fields = (
        "asset_id",
        "name",
        "serial_number",
        "property_code",
    )

    list_filter = (
        "category",
        "status",
    )

    @admin.display(description="Warranty Status")
    def warranty_status(self, obj):
        if not obj.warranty_expiry:
            return "No Warranty"

        from datetime import date

        if obj.warranty_expiry < date.today():
            return "Expired"

        return "Valid"

    @admin.display(description="Warranty Alert")
    def warranty_alert(self, obj):
        if not obj.warranty_expiry:
            return "No Warranty"

        from datetime import date, timedelta

        today = date.today()
        alert_date = today + timedelta(days=10)

        if today <= obj.warranty_expiry <= alert_date:
            return "Expiring Soon"

        return "No Alert"

    class Media:
        js = ("core/asset_specifications.js",)


@admin.register(AssetSpecification)
class AssetSpecificationAdmin(admin.ModelAdmin):
    list_display = ("asset", "definition", "value")
    search_fields = ("asset__asset_id", "asset__name", "value")
    list_filter = ("definition__category",)


class RequestHandlingInline(admin.TabularInline):

    model = RequestHandling
    form = RequestHandlingForm
    extra = 0

    fields = (
        "asset",
        "warranty_status",
        "technician",
        "handled_date",
        "repair_location",
        "repair_performed_by",
        "repair_result",
        "next_action",
        "workshop_result",
        "external_approval",
        "external_repair_result",
        "replacement_asset",
        "replacement_type",
        "result",
    )

    readonly_fields = (
        "handled_date",
    )


class RequestForm(forms.ModelForm):

    class Meta:
        model = Request
        fields = "__all__"

    class Media:
        js = ("core/request.js",)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):

    form = RequestForm

    inlines = [RequestHandlingInline]

    list_display = (
        "title",
        "display_requester",
        "requester",
        "priority",
        "status",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "requester__name",
        "requester_profile__name",
    )

    list_filter = ("priority", "status", "requester")

    @admin.display(description="Requester")
    def display_requester(self, obj):
        if obj.requester_profile:
            return obj.requester_profile.name
        return "-"


@admin.register(RequestHandling)
class RequestHandlingAdmin(admin.ModelAdmin):

    form = RequestHandlingForm

    list_display = (
        "request",
        "asset",
        "technician",
        "handled_date",
        "repair_location",
        "repair_performed_by",
        "repair_result",
        "workshop_result",
        "external_approval",
        "external_repair_result",
        "replacement_asset",
        "replacement_type",
    )

    search_fields = (
        "request__title",
        "asset__asset_id",
        "asset__name",
        "asset__serial_number",
        "asset__property_code",
        "technician__name",
        "result",
    )

    list_filter = (
        "repair_location",
        "repair_performed_by",
        "repair_result",
        "next_action",
        "workshop_result",
        "external_approval",
        "external_repair_result",
    )

    class Media:
        js = ("core/request_handling.js",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "contract_number",
        "contract_type",
        "provider",
        "start_date",
        "end_date",
        "status",
    )

    search_fields = (
        "title",
        "contract_number",
        "provider",
        "description",
        "notes",
    )

    list_filter = (
        "contract_type",
        "status",
    )

    date_hierarchy = "end_date"

