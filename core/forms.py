from django import forms

from .models import Asset, RequestHandling


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
            try:
                asset = Asset.objects.get(pk=value)
                option["attrs"]["data-warranty-status"] = (
                    asset.warranty_status
                )
            except (Asset.DoesNotExist, ValueError, TypeError):
                pass

        return option


class RequestHandlingForm(forms.ModelForm):

    class Meta:
        model = RequestHandling

        fields = [
            "asset",
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

            "handled_date": forms.DateInput(
                attrs={"type": "date"}
            ),

            "result": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Enter the final result or notes..."
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        external_repair_result = cleaned_data.get(
            "external_repair_result"
        )

        external_approval = cleaned_data.get(
            "external_approval"
        )

        if (
            external_repair_result == "PAID_REPAIR"
            and external_approval != "APPROVED"
        ):
            raise forms.ValidationError(
                "Paid External Repair requires Principal Approval."
            )

        next_action = cleaned_data.get("next_action")

        workshop_result = cleaned_data.get(
            "workshop_result"
        )

        replacement_asset = cleaned_data.get(
            "replacement_asset"
        )

        is_replacement = (
            next_action == "REPLACEMENT"
            or workshop_result == "REPLACEMENT"
        )

        if is_replacement and not replacement_asset:
            self.add_error(
                "replacement_asset",
                "Replacement Asset is required for Replacement."
            )

        return cleaned_data