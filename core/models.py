
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Location(models.Model):

    LOCATION_TYPE_CHOICES = [
        ("BUILDING", "Building"),
        ("FLOOR", "Floor"),
        ("AREA", "Area"),
        ("OUTDOOR", "Outdoor"),
    ]

    name = models.CharField(max_length=150)

    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        default="AREA",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ["name"]

    def clean(self):
        super().clean()

        # ---------------------------------------------------------
        # A location cannot be its own parent.
        # ---------------------------------------------------------
        if self.pk and self.parent_id == self.pk:
            raise ValidationError(
                "A location cannot be its own parent."
            )

        # ---------------------------------------------------------
        # Prevent circular parent relationships.
        # ---------------------------------------------------------
        parent = self.parent

        while parent is not None:
            if self.pk and parent.pk == self.pk:
                raise ValidationError(
                    "Circular location hierarchy is not allowed."
                )

            parent = parent.parent

        # ---------------------------------------------------------
        # BUILDING
        # ---------------------------------------------------------
        if self.location_type == "BUILDING":

            if self.parent is not None:
                raise ValidationError(
                    "A Building cannot have a parent location."
                )

        # ---------------------------------------------------------
        # FLOOR
        # ---------------------------------------------------------
        elif self.location_type == "FLOOR":

            if self.parent is None:
                raise ValidationError(
                    "A Floor must belong to a Building."
                )

            if self.parent.location_type != "BUILDING":
                raise ValidationError(
                    "A Floor must belong directly to a Building."
                )

        # ---------------------------------------------------------
        # AREA
        # ---------------------------------------------------------
        elif self.location_type == "AREA":

            if self.parent is None:
                raise ValidationError(
                    "An Area must belong to a Building or Floor."
                )

            if self.parent.location_type not in [
                "BUILDING",
                "FLOOR",
                "AREA",
            ]:
                raise ValidationError(
                    "An Area can only belong to a Building, Floor, "
                    "or another Area."
                )

        # ---------------------------------------------------------
        # OUTDOOR
        # ---------------------------------------------------------
        elif self.location_type == "OUTDOOR":

            if self.parent is not None:
                raise ValidationError(
                    "An Outdoor location cannot have a parent."
                )

    def __str__(self):
        return self.name


class SpecificationDefinition(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Personnel(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Requester(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=100)

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
    )

    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.unit.name}"


class Asset(models.Model):
    asset_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    property_code = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("ACTIVE", "Active"),
            ("IN_REPAIR", "In Repair"),
            ("IN_STORAGE", "In Storage"),
            ("RETIRED", "Retired"),
        ],
        default="ACTIVE",
    )

    warranty_expiry = models.DateField(
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    used_in = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    @property
    def warranty_status(self):
        from datetime import date

        if not self.warranty_expiry:
            return "No Warranty"

        if self.warranty_expiry < date.today():
            return "Expired"

        return "Valid"

    def __str__(self):
        return f"{self.asset_id} - {self.name}"


class AssetSpecification(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
    )

    definition = models.ForeignKey(
        SpecificationDefinition,
        on_delete=models.PROTECT,
    )

    value = models.CharField(
        max_length=255,
        blank=True,
    )

    def __str__(self):
        return f"{self.asset} - {self.definition.name}: {self.value}"


class Request(models.Model):
    PRIORITY_CHOICES = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("NEW", "New"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    title = models.CharField(max_length=200)

    description = models.TextField()

    # Existing relationship.
    # Kept temporarily so existing Requests remain connected
    # to their original Units.
    requester = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
    )

    # New relationship to the actual requester.
    requester_profile = models.ForeignKey(
        Requester,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requests",
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="NORMAL",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="NEW",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    attachment = models.FileField(
        upload_to="request_attachments/",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.title


class RequestHandling(models.Model):
    REPAIR_LOCATION_CHOICES = [
        ("ON_SITE", "On-Site"),
        ("WORKSHOP", "IT Workshop"),
        ("EXTERNAL", "External Repair"),
    ]

    PERFORMED_BY_CHOICES = [
        ("IT_PERSONNEL", "IT Personnel"),
        ("EXTERNAL", "External Person/Company"),
    ]

    REPAIR_RESULT_CHOICES = [
        ("REPAIRED", "Repaired"),
        ("NOT_REPAIRED", "Not Repaired"),
        ("FURTHER_ACTION", "Needs Further Action"),
    ]

    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    technician = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
    )

    handled_date = models.DateField()

    repair_location = models.CharField(
        max_length=20,
        choices=REPAIR_LOCATION_CHOICES,
        default="ON_SITE",
    )

    repair_performed_by = models.CharField(
        max_length=20,
        choices=PERFORMED_BY_CHOICES,
        default="IT_PERSONNEL",
    )

    repair_result = models.CharField(
        max_length=20,
        choices=REPAIR_RESULT_CHOICES,
        default="REPAIRED",
    )

    NEXT_ACTION_CHOICES = [
        ("NONE", "None / Finished"),
        ("WORKSHOP", "IT Workshop"),
        ("EXTERNAL", "External Repair"),
        ("REPLACEMENT", "Replacement"),
    ]

    next_action = models.CharField(
        max_length=20,
        choices=NEXT_ACTION_CHOICES,
        default="NONE",
    )

    workshop_result = models.CharField(
        max_length=30,
        choices=[
            ("REPAIRED", "Repaired"),
            ("CANNOT_REPAIR", "Cannot be Repaired"),
            ("EXTERNAL_REPAIR", "Sent to External Repair"),
            ("REPLACEMENT", "Replacement Required"),
        ],
        blank=True,
    )

    EXTERNAL_APPROVAL_CHOICES = [
        ("NOT_REQUIRED", "Not Required"),
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    external_approval = models.CharField(
        max_length=20,
        choices=EXTERNAL_APPROVAL_CHOICES,
        default="NOT_REQUIRED",
    )

    external_repair_result = models.CharField(
        max_length=30,
        choices=[
            ("PAID_REPAIR", "Paid External Repair"),
            ("NOT_REPAIRED", "Not Repaired"),
            ("RETURNED", "Returned"),
        ],
        blank=True,
    )

    REPLACEMENT_TYPE_CHOICES = [
        ("TEMPORARY", "Temporary Replacement"),
        ("PERMANENT", "Permanent Replacement"),
    ]

    replacement_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="replacement_for",
    )

    replacement_type = models.CharField(
        max_length=20,
        choices=REPLACEMENT_TYPE_CHOICES,
        blank=True,
    )

    result = models.TextField(
        blank=True,
    )

    def clean(self):
        super().clean()

        if (
            self.external_repair_result == "PAID_REPAIR"
            and self.external_approval != "APPROVED"
        ):
            raise ValidationError(
                "Paid External Repair requires Principal Approval."
            )

        is_replacement = (
            self.next_action == "REPLACEMENT"
            or self.workshop_result == "REPLACEMENT"
        )

        if is_replacement and not self.replacement_asset:
            raise ValidationError(
                "Replacement Asset is required for Replacement."
            )

    def __str__(self):
        return (
            f"{self.request} - "
            f"{self.technician} - "
            f"{self.handled_date}"
        )


# =========================================================
# CONTRACTS
# =========================================================

class Contract(models.Model):

    CONTRACT_TYPE_CHOICES = [
        ("INTERNET", "Internet / Network Service"),
        ("MAINTENANCE", "Maintenance"),
        ("SOFTWARE", "Software"),
        ("SUPPORT", "Support"),
        ("EQUIPMENT_SERVICE", "Equipment / Service"),
        ("OTHER", "Other"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    title = models.CharField(
        max_length=200,
    )

    contract_number = models.CharField(
        max_length=100,
        blank=True,
    )

    contract_type = models.CharField(
        max_length=30,
        choices=CONTRACT_TYPE_CHOICES,
        default="OTHER",
    )

    provider = models.CharField(
        max_length=200,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    description = models.TextField(
        blank=True,
    )

    document = models.FileField(
        upload_to="contracts/",
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-start_date", "title"]
        verbose_name = "Contract"
        verbose_name_plural = "Contracts"

    def __str__(self):
        if self.contract_number:
            return f"{self.title} - {self.contract_number}"

        return self.title

