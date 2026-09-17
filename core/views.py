
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db.models import Q, Prefetch
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .models import (
    Asset,
    Category,
    Location,
    Request,
    Requester,
    RequestHandling,
    Unit,
    Contract,
)
from .forms import RequestHandlingForm


# =========================================================
# DASHBOARD
# =========================================================

def dashboard(request):
    total_assets = Asset.objects.count()

    in_repair = Asset.objects.filter(
        status="IN_REPAIR"
    ).count()

    in_storage = Asset.objects.filter(
        status="IN_STORAGE"
    ).count()

    today = timezone.localdate()

    warranty_expiring = Asset.objects.filter(
        warranty_expiry__gte=today,
        warranty_expiry__lte=today + timedelta(days=10),
    ).count()

    expired_warranty = Asset.objects.filter(
        warranty_expiry__lt=today
    ).count()

    new_requests = Request.objects.filter(
        status="NEW"
    ).count()

    assets = Asset.objects.select_related(
        "category",
        "location",
        "used_in",
    ).all()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    category_id = request.GET.get(
        "category",
        ""
    ).strip()

    unit_id = request.GET.get(
        "unit",
        ""
    ).strip()

    building_id = request.GET.get(
        "building",
        ""
    ).strip()

    floor_id = request.GET.get(
        "floor",
        ""
    ).strip()

    area_id = request.GET.get(
        "area",
        ""
    ).strip()

    asset_status = request.GET.get(
        "status",
        ""
    ).strip()

    warranty = request.GET.get(
        "warranty",
        ""
    ).strip()

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    if search:
        assets = assets.filter(
            Q(asset_id__icontains=search)
            | Q(name__icontains=search)
            | Q(serial_number__icontains=search)
            | Q(property_code__icontains=search)
        )

    # -----------------------------------------------------
    # Category
    # -----------------------------------------------------

    if category_id:
        assets = assets.filter(
            category_id=category_id
        )

    # -----------------------------------------------------
    # Used In / Unit
    # -----------------------------------------------------

    if unit_id:
        assets = assets.filter(
            used_in_id=unit_id
        )

    # -----------------------------------------------------
    # Location Hierarchy
    # -----------------------------------------------------

    selected_location_ids = set()

    def get_descendant_ids(parent_id):
        descendants = {parent_id}
        pending = [parent_id]

        while pending:
            current_id = pending.pop()

            child_ids = list(
                Location.objects.filter(
                    parent_id=current_id
                ).values_list(
                    "id",
                    flat=True
                )
            )

            for child_id in child_ids:
                if child_id not in descendants:
                    descendants.add(child_id)
                    pending.append(child_id)

        return descendants

    # -----------------------------------------------------
    # Building Filter
    # -----------------------------------------------------

    if building_id:
        selected_location_ids.update(
            get_descendant_ids(
                int(building_id)
            )
        )

    # -----------------------------------------------------
    # Floor Filter
    # -----------------------------------------------------

    if floor_id:
        floor_location_ids = get_descendant_ids(
            int(floor_id)
        )

        if selected_location_ids:
            selected_location_ids &= floor_location_ids
        else:
            selected_location_ids = floor_location_ids

    # -----------------------------------------------------
    # Area / Room Filter
    # -----------------------------------------------------

    if area_id:
        area_location_ids = get_descendant_ids(
            int(area_id)
        )

        if selected_location_ids:
            selected_location_ids &= area_location_ids
        else:
            selected_location_ids = area_location_ids

    if building_id or floor_id or area_id:
        assets = assets.filter(
            location_id__in=selected_location_ids
        )

    # -----------------------------------------------------
    # Status
    # -----------------------------------------------------

    if asset_status:
        assets = assets.filter(
            status=asset_status
        )

    # -----------------------------------------------------
    # Warranty
    # -----------------------------------------------------

    if warranty == "NO_WARRANTY":
        assets = assets.filter(
            warranty_expiry__isnull=True
        )

    elif warranty == "EXPIRED":
        assets = assets.filter(
            warranty_expiry__isnull=False,
            warranty_expiry__lt=today,
        )

    elif warranty == "EXPIRING":
        assets = assets.filter(
            warranty_expiry__gte=today,
            warranty_expiry__lte=today + timedelta(days=10),
        )

    elif warranty == "VALID":
        assets = assets.filter(
            warranty_expiry__gt=today + timedelta(days=10)
        )

    assets = assets.order_by(
        "asset_id"
    )

    # -----------------------------------------------------
    # Filter Options
    # -----------------------------------------------------

    categories = Category.objects.all().order_by(
        "name"
    )

    units = Unit.objects.all().order_by(
        "name"
    )

    buildings = Location.objects.filter(
        location_type="BUILDING",
        is_active=True,
    ).order_by(
        "name"
    )

    floors = Location.objects.filter(
        location_type="FLOOR",
        is_active=True,
    ).order_by(
        "name"
    )

    areas = Location.objects.filter(
        Q(location_type="AREA")
        | Q(location_type="OUTDOOR"),
        is_active=True,
    ).order_by(
        "name"
    )

    # -----------------------------------------------------
    # Dashboard Response
    # -----------------------------------------------------

    return render(
        request,
        "core/dashboard.html",
        {
            "total_assets": total_assets,
            "in_repair": in_repair,
            "in_storage": in_storage,
            "warranty_expiring": warranty_expiring,
            "expired_warranty": expired_warranty,
            "new_requests": new_requests,

            "assets": assets,

            "search": search,
            "selected_category": category_id,
            "selected_unit": unit_id,
            "selected_building": building_id,
            "selected_floor": floor_id,
            "selected_area": area_id,
            "selected_status": asset_status,
            "selected_warranty": warranty,

            "categories": categories,
            "units": units,
            "buildings": buildings,
            "floors": floors,
            "areas": areas,

            "status_choices": [
                ("ACTIVE", "Active"),
                ("IN_REPAIR", "In Repair"),
                ("IN_STORAGE", "In Storage"),
                ("RETIRED", "Retired"),
            ],
        },
    )


# =========================================================
# REPORTS
# =========================================================

@staff_member_required
def reports(request):
    today = timezone.localdate()

    # -----------------------------------------------------
    # Report Type
    # -----------------------------------------------------

    report_type = request.GET.get(
        "report_type",
        "assets"
    ).strip()

    valid_report_types = {
        "assets",
        "warranty",
        "requests",
        "locations",
        "contracts",
    }

    if report_type not in valid_report_types:
        report_type = "assets"

    # -----------------------------------------------------
    # Asset Filter Values
    # -----------------------------------------------------

    category_id = request.GET.get(
        "category",
        ""
    ).strip()

    unit_id = request.GET.get(
        "unit",
        ""
    ).strip()

    building_id = request.GET.get(
        "building",
        ""
    ).strip()

    floor_id = request.GET.get(
        "floor",
        ""
    ).strip()

    area_id = request.GET.get(
        "area",
        ""
    ).strip()

    asset_status = request.GET.get(
        "status",
        ""
    ).strip()

    warranty = request.GET.get(
        "warranty",
        ""
    ).strip()

    # -----------------------------------------------------
    # Request Filter Values
    # -----------------------------------------------------

    request_status = request.GET.get(
        "request_status",
        ""
    ).strip()

    request_priority = request.GET.get(
        "request_priority",
        ""
    ).strip()

    request_unit_id = request.GET.get(
        "request_unit",
        ""
    ).strip()

    # -----------------------------------------------------
    # Contract Filter Values
    # -----------------------------------------------------

    contract_search = request.GET.get(
        "contract_search",
        ""
    ).strip()

    contract_type = request.GET.get(
        "contract_type",
        ""
    ).strip()

    contract_provider = request.GET.get(
        "contract_provider",
        ""
    ).strip()

    contract_status = request.GET.get(
        "contract_status",
        ""
    ).strip()

    contract_start_from = request.GET.get(
        "contract_start_from",
        ""
    ).strip()

    contract_start_to = request.GET.get(
        "contract_start_to",
        ""
    ).strip()

    contract_end_from = request.GET.get(
        "contract_end_from",
        ""
    ).strip()

    contract_end_to = request.GET.get(
        "contract_end_to",
        ""
    ).strip()

    # -----------------------------------------------------
    # Filter Options
    # -----------------------------------------------------

    categories = Category.objects.all().order_by(
        "name"
    )

    units = Unit.objects.all().order_by(
        "name"
    )

    buildings = Location.objects.filter(
        location_type="BUILDING",
        is_active=True,
    ).order_by(
        "name"
    )

    floors = Location.objects.filter(
        location_type="FLOOR",
        is_active=True,
    ).order_by(
        "name"
    )

    areas = Location.objects.filter(
        Q(location_type="AREA")
        | Q(location_type="OUTDOOR"),
        is_active=True,
    ).order_by(
        "name"
    )

    # -----------------------------------------------------
    # Contract Filter Options
    # -----------------------------------------------------

    contract_type_choices = Contract.CONTRACT_TYPE_CHOICES

    contract_status_choices = Contract.STATUS_CHOICES

    # -----------------------------------------------------
    # Location Hierarchy Helper
    # -----------------------------------------------------

    def get_descendant_ids(parent_id):
        descendants = {parent_id}
        pending = [parent_id]

        while pending:
            current_id = pending.pop()

            child_ids = list(
                Location.objects.filter(
                    parent_id=current_id,
                    is_active=True,
                ).values_list(
                    "id",
                    flat=True
                )
            )

            for child_id in child_ids:
                if child_id not in descendants:
                    descendants.add(child_id)
                    pending.append(child_id)

        return descendants

    # -----------------------------------------------------
    # Report Variables
    # -----------------------------------------------------

    report_title = "Asset Report"

    report_description = (
        "Generate a report using the selected asset filters."
    )

    assets = Asset.objects.select_related(
        "category",
        "location",
        "used_in",
    ).none()

    requests = Request.objects.select_related(
        "requester_profile",
        "requester",
    ).none()

    location_results = Location.objects.none()

    contracts = Contract.objects.none()

    # =====================================================
    # ASSET REPORT
    # =====================================================

    if report_type == "assets":

        report_title = "IT Asset Report"

        report_description = (
            "Assets matching the selected category, unit, "
            "location, status, and warranty filters."
        )

        assets = Asset.objects.select_related(
            "category",
            "location",
            "used_in",
        ).all()

        # -------------------------------------------------
        # Category
        # -------------------------------------------------

        if category_id:
            assets = assets.filter(
                category_id=category_id
            )

        # -------------------------------------------------
        # Used In / Unit
        # -------------------------------------------------

        if unit_id:
            assets = assets.filter(
                used_in_id=unit_id
            )

        # -------------------------------------------------
        # Location Hierarchy
        # -------------------------------------------------

        selected_location_ids = set()

        if building_id:
            try:
                selected_location_ids.update(
                    get_descendant_ids(
                        int(building_id)
                    )
                )
            except ValueError:
                building_id = ""

        if floor_id:
            try:
                floor_location_ids = get_descendant_ids(
                    int(floor_id)
                )

                if selected_location_ids:
                    selected_location_ids &= floor_location_ids
                else:
                    selected_location_ids = floor_location_ids

            except ValueError:
                floor_id = ""

        if area_id:
            try:
                area_location_ids = get_descendant_ids(
                    int(area_id)
                )

                if selected_location_ids:
                    selected_location_ids &= area_location_ids
                else:
                    selected_location_ids = area_location_ids

            except ValueError:
                area_id = ""

        if building_id or floor_id or area_id:
            assets = assets.filter(
                location_id__in=selected_location_ids
            )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        if asset_status:
            assets = assets.filter(
                status=asset_status
            )

        # -------------------------------------------------
        # Warranty
        # -------------------------------------------------

        if warranty == "NO_WARRANTY":

            assets = assets.filter(
                warranty_expiry__isnull=True
            )

        elif warranty == "EXPIRED":

            assets = assets.filter(
                warranty_expiry__isnull=False,
                warranty_expiry__lt=today,
            )

        elif warranty == "EXPIRING":

            assets = assets.filter(
                warranty_expiry__gte=today,
                warranty_expiry__lte=(
                    today + timedelta(days=10)
                ),
            )

        elif warranty == "VALID":

            assets = assets.filter(
                warranty_expiry__gt=(
                    today + timedelta(days=10)
                )
            )

        assets = assets.order_by(
            "asset_id"
        )

    # =====================================================
    # WARRANTY REPORT
    # =====================================================

    elif report_type == "warranty":

        report_title = "Warranty Report"

        report_description = (
            "IT assets grouped and filtered according to "
            "their current warranty condition."
        )

        assets = Asset.objects.select_related(
            "category",
            "location",
            "used_in",
        ).all()

        # -------------------------------------------------
        # Optional Asset Filters
        # -------------------------------------------------

        if category_id:
            assets = assets.filter(
                category_id=category_id
            )

        if unit_id:
            assets = assets.filter(
                used_in_id=unit_id
            )

        # -------------------------------------------------
        # Location Hierarchy
        # -------------------------------------------------

        selected_location_ids = set()

        if building_id:
            try:
                selected_location_ids.update(
                    get_descendant_ids(
                        int(building_id)
                    )
                )
            except ValueError:
                building_id = ""

        if floor_id:
            try:
                floor_location_ids = get_descendant_ids(
                    int(floor_id)
                )

                if selected_location_ids:
                    selected_location_ids &= floor_location_ids
                else:
                    selected_location_ids = floor_location_ids

            except ValueError:
                floor_id = ""

        if area_id:
            try:
                area_location_ids = get_descendant_ids(
                    int(area_id)
                )

                if selected_location_ids:
                    selected_location_ids &= area_location_ids
                else:
                    selected_location_ids = area_location_ids

            except ValueError:
                area_id = ""

        if building_id or floor_id or area_id:
            assets = assets.filter(
                location_id__in=selected_location_ids
            )

        # -------------------------------------------------
        # Warranty Condition
        # -------------------------------------------------

        if warranty == "NO_WARRANTY":

            assets = assets.filter(
                warranty_expiry__isnull=True
            )

            report_title = "Assets with No Warranty"

        elif warranty == "EXPIRED":

            assets = assets.filter(
                warranty_expiry__isnull=False,
                warranty_expiry__lt=today,
            )

            report_title = "Expired Warranty"

        elif warranty == "EXPIRING":

            assets = assets.filter(
                warranty_expiry__gte=today,
                warranty_expiry__lte=(
                    today + timedelta(days=10)
                ),
            )

            report_title = "Warranty Expiring Soon"

        elif warranty == "VALID":

            assets = assets.filter(
                warranty_expiry__gt=(
                    today + timedelta(days=10)
                )
            )

            report_title = "Valid Warranty"

        else:

            report_title = "Warranty Report"

        assets = assets.order_by(
            "warranty_expiry",
            "asset_id",
        )

    # =====================================================
    # REQUEST REPORT
    # =====================================================

    elif report_type == "requests":

        report_title = "Request Report"

        report_description = (
            "Service requests filtered by status, priority, "
            "and requesting unit."
        )

        requests = Request.objects.select_related(
            "requester_profile",
            "requester",
        ).order_by(
            "-created_at"
        )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        if request_status:
            requests = requests.filter(
                status=request_status
            )

        # -------------------------------------------------
        # Priority
        # -------------------------------------------------

        if request_priority:
            requests = requests.filter(
                priority=request_priority
            )

        # -------------------------------------------------
        # Requesting Unit
        # -------------------------------------------------

        if request_unit_id:
            requests = requests.filter(
                requester_id=request_unit_id
            )

    # =====================================================
    # LOCATION REPORT
    # =====================================================

    elif report_type == "locations":

        report_title = "Location Report"

        report_description = (
            "Locations currently registered in the IT Asset "
            "Management System."
        )

        location_results = Location.objects.filter(
            is_active=True
        ).select_related(
            "parent"
        ).order_by(
            "location_type",
            "name"
        )

        # -------------------------------------------------
        # Location Type Filter
        # -------------------------------------------------

        location_type = request.GET.get(
            "location_type",
            ""
        ).strip()

        if location_type in {
            "BUILDING",
            "FLOOR",
            "AREA",
            "OUTDOOR",
        }:
            location_results = location_results.filter(
                location_type=location_type
            )

        # -------------------------------------------------
        # Parent / Building Filter
        # -------------------------------------------------

        if building_id:
            try:
                location_ids = get_descendant_ids(
                    int(building_id)
                )

                location_results = location_results.filter(
                    id__in=location_ids
                )

            except ValueError:
                building_id = ""

    # =====================================================
    # CONTRACT REPORT
    # =====================================================

    elif report_type == "contracts":

        report_title = "Contract Report"

        report_description = (
            "Contracts matching the selected search, type, "
            "provider, status, and date filters."
        )

        contracts = Contract.objects.all()

        # -------------------------------------------------
        # Search
        # -------------------------------------------------

        if contract_search:
            contracts = contracts.filter(
                Q(title__icontains=contract_search)
                | Q(contract_number__icontains=contract_search)
                | Q(provider__icontains=contract_search)
                | Q(description__icontains=contract_search)
                | Q(notes__icontains=contract_search)
            )

        # -------------------------------------------------
        # Contract Type
        # -------------------------------------------------

        if contract_type:
            contracts = contracts.filter(
                contract_type=contract_type
            )

        # -------------------------------------------------
        # Provider
        # -------------------------------------------------

        if contract_provider:
            contracts = contracts.filter(
                provider__icontains=contract_provider
            )

        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        if contract_status:
            contracts = contracts.filter(
                status=contract_status
            )

        # -------------------------------------------------
        # Start Date From
        # -------------------------------------------------

        if contract_start_from:
            contracts = contracts.filter(
                start_date__gte=contract_start_from
            )

        # -------------------------------------------------
        # Start Date To
        # -------------------------------------------------

        if contract_start_to:
            contracts = contracts.filter(
                start_date__lte=contract_start_to
            )

        # -------------------------------------------------
        # End Date From
        # -------------------------------------------------

        if contract_end_from:
            contracts = contracts.filter(
                end_date__gte=contract_end_from
            )

        # -------------------------------------------------
        # End Date To
        # -------------------------------------------------

        if contract_end_to:
            contracts = contracts.filter(
                end_date__lte=contract_end_to
            )

        contracts = contracts.order_by(
            "-start_date",
            "title",
        )

    # =====================================================
    # Display Choices
    # =====================================================

    report_types = [
        (
            "assets",
            "Assets",
        ),
        (
            "warranty",
            "Warranty",
        ),
        (
            "requests",
            "Requests",
        ),
        (
            "locations",
            "Locations",
        ),
        (
            "contracts",
            "Contracts",
        ),
    ]

    status_choices = [
        ("ACTIVE", "Active"),
        ("IN_REPAIR", "In Repair"),
        ("IN_STORAGE", "In Storage"),
        ("RETIRED", "Retired"),
    ]

    warranty_choices = [
        ("VALID", "Valid"),
        ("EXPIRING", "Expiring Soon"),
        ("EXPIRED", "Expired"),
        ("NO_WARRANTY", "No Warranty"),
    ]

    request_status_choices = [
        ("NEW", "New"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    request_priority_choices = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
    ]

    location_type_choices = [
        ("BUILDING", "Building"),
        ("FLOOR", "Floor"),
        ("AREA", "Area / Room"),
        ("OUTDOOR", "Outdoor"),
    ]

    # -----------------------------------------------------
    # Report Counts
    # -----------------------------------------------------

    if report_type in {
        "assets",
        "warranty",
    }:
        report_count = assets.count()

    elif report_type == "requests":
        report_count = requests.count()

    elif report_type == "locations":
        report_count = location_results.count()

    else:
        report_count = contracts.count()

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return render(
        request,
        "core/reports.html",
        {
            # Report data
            "assets": assets,
            "requests": requests,
            "location_results": location_results,
            "contracts": contracts,

            # Report state
            "report_type": report_type,
            "report_title": report_title,
            "report_description": report_description,
            "report_count": report_count,
            "today": today,

            # Report types
            "report_types": report_types,

            # Asset filters
            "categories": categories,
            "units": units,
            "buildings": buildings,
            "floors": floors,
            "areas": areas,

            "selected_category": category_id,
            "selected_unit": unit_id,
            "selected_building": building_id,
            "selected_floor": floor_id,
            "selected_area": area_id,
            "selected_status": asset_status,
            "selected_warranty": warranty,

            "status_choices": status_choices,
            "warranty_choices": warranty_choices,

            # Request filters
            "selected_request_status": request_status,
            "selected_request_priority": request_priority,
            "selected_request_unit": request_unit_id,

            "request_status_choices": request_status_choices,
            "request_priority_choices": request_priority_choices,

            # Location filters
            "selected_location_type": request.GET.get(
                "location_type",
                ""
            ).strip(),

            "location_type_choices": location_type_choices,

            # Contract filters
            "contract_type_choices": contract_type_choices,
            "contract_status_choices": contract_status_choices,

            "selected_contract_search": contract_search,
            "selected_contract_type": contract_type,
            "selected_contract_provider": contract_provider,
            "selected_contract_status": contract_status,

            "selected_contract_start_from": contract_start_from,
            "selected_contract_start_to": contract_start_to,
            "selected_contract_end_from": contract_end_from,
            "selected_contract_end_to": contract_end_to,
        },
    )


# =========================================================
# LOCATION MANAGEMENT
# =========================================================

@staff_member_required
def location_management(request):
    locations = Location.objects.filter(
        is_active=True
    ).select_related(
        "parent"
    ).order_by(
        "name"
    )

    location_map = {
        location.pk: {
            "location": location,
            "children": [],
        }
        for location in locations
    }

    root_locations = []

    for location in locations:
        node = location_map[location.pk]

        if location.parent_id:
            parent_node = location_map.get(
                location.parent_id
            )

            if parent_node:
                parent_node["children"].append(node)
            else:
                root_locations.append(node)

        else:
            root_locations.append(node)

    # -----------------------------------------------------
    # Sort Location Tree
    # -----------------------------------------------------

    def sort_children(node):
        node["children"].sort(
            key=lambda item: item["location"].name.lower()
        )

        for child in node["children"]:
            sort_children(child)

    root_locations.sort(
        key=lambda item: item["location"].name.lower()
    )

    for root in root_locations:
        sort_children(root)

    return render(
        request,
        "core/location_management.html",
        {
            "locations": root_locations,
        },
    )


# =========================================================
# LOCATION CREATE
# =========================================================

@staff_member_required
def location_create(request):
    active_locations = Location.objects.filter(
        is_active=True
    ).select_related(
        "parent"
    ).order_by(
        "name"
    )

    errors = []

    if request.method == "POST":
        name = request.POST.get(
            "name",
            ""
        ).strip()

        location_type = request.POST.get(
            "location_type",
            "AREA"
        ).strip()

        parent_id = request.POST.get(
            "parent",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        if not name:
            errors.append(
                "Location name is required."
            )

        valid_types = {
            choice[0]
            for choice in Location.LOCATION_TYPE_CHOICES
        }

        if location_type not in valid_types:
            errors.append(
                "Invalid location type."
            )

        parent = None

        if parent_id:
            try:
                parent = Location.objects.get(
                    pk=int(parent_id),
                    is_active=True,
                )
            except (
                Location.DoesNotExist,
                ValueError,
            ):
                errors.append(
                    "The selected parent location is invalid."
                )

        if not errors:
            location = Location(
                name=name,
                location_type=location_type,
                parent=parent,
                description=description,
                is_active=True,
            )

            try:
                location.full_clean()
                location.save()

                return redirect(
                    "location_management"
                )

            except ValidationError as exc:
                errors.extend(
                    exc.messages
                )

    return render(
        request,
        "core/location_create.html",
        {
            "location_types": Location.LOCATION_TYPE_CHOICES,
            "active_locations": active_locations,
            "errors": errors,
            "form_name": request.POST.get(
                "name",
                ""
            ),
            "form_type": request.POST.get(
                "location_type",
                "AREA"
            ),
            "form_parent": request.POST.get(
                "parent",
                ""
            ),
            "form_description": request.POST.get(
                "description",
                ""
            ),
        },
    )


# =========================================================
# UNIFIED LOGIN
# =========================================================

class RequesterLoginView(LoginView):
    template_name = "core/requester_login.html"

    def get_success_url(self):
        """
        Send users to the correct application area
        according to their role.
        """

        user = self.request.user

        # IT Manager / staff users
        if user.is_staff or user.is_superuser:
            return reverse("dashboard")

        # Requesters
        return reverse("requester")


# =========================================================
# REQUESTER
# =========================================================

@login_required
def requester_page(request):
    requester = Requester.objects.filter(
        user=request.user
    ).first()

    # -----------------------------------------------------
    # The logged-in user must have a Requester profile.
    # If not, return to the requester login page instead
    # of raising "Requester matching query does not exist."
    # -----------------------------------------------------

    if requester is None:
        return redirect("login")

    if request.method == "POST":
        title = request.POST.get(
            "title",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        attachment = request.FILES.get(
            "attachment"
        )

        if title and description:
            if requester.unit.name in [
                "Principal Dr. Jasem Office",
                "Principal Dr. Hadi Office",
            ]:
                priority = "URGENT"
            else:
                priority = "NORMAL"

            Request.objects.create(
                title=title,
                description=description,
                requester=requester.unit,
                requester_profile=requester,
                priority=priority,
                status="NEW",
                attachment=attachment,
            )

            return redirect(
                "requester"
            )

    my_requests = Request.objects.filter(
        requester_profile=requester
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "core/requester.html",
        {
            "requester": requester,
            "my_requests": my_requests,
        },
    )


# =========================================================
# REQUEST LIST
# =========================================================

@staff_member_required
def request_list(request):
    requests = Request.objects.select_related(
        "requester_profile",
        "requester",
    ).prefetch_related(
        Prefetch(
            "requesthandling_set",
            queryset=RequestHandling.objects.select_related(
                "asset"
            ),
            to_attr="handling_records",
        )
    ).order_by(
        "-created_at"
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:
        requests = requests.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(
                requester_profile__name__icontains=search
            )
            | Q(
                requester__name__icontains=search
            )
        )

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status:
        requests = requests.filter(
            status=status
        )

    priority = request.GET.get(
        "priority",
        ""
    ).strip()

    if priority:
        requests = requests.filter(
            priority=priority
        )

    return render(
        request,
        "core/request_list.html",
        {
            "requests": requests,
            "search": search,
            "selected_status": status,
            "selected_priority": priority,
            "status_choices": Request.STATUS_CHOICES,
            "priority_choices": Request.PRIORITY_CHOICES,
        },
    )


# =========================================================
# REQUEST DETAIL
# =========================================================

@staff_member_required
def request_detail(request, pk):
    request_record = get_object_or_404(
        Request.objects.select_related(
            "requester_profile",
            "requester",
        ).prefetch_related(
            "requesthandling_set__asset",
            "requesthandling_set__technician",
        ),
        pk=pk,
    )

    handling = request_record.requesthandling_set.order_by(
        "-handled_date"
    ).first()

    form = None

    # -----------------------------------------------------
    # TERMINAL REQUESTS
    # -----------------------------------------------------

    if request_record.status in [
        "COMPLETED",
        "CANCELLED",
    ]:
        if handling:
            form = RequestHandlingForm(
                instance=handling
            )
        else:
            form = RequestHandlingForm()

        for field in form.fields.values():
            field.disabled = True

        return render(
            request,
            "core/request_detail.html",
            {
                "request_record": request_record,
                "handling": handling,
                "form": form,
            },
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        if request.POST.get(
            "cancel_request"
        ) == "1":

            if request_record.status in [
                "NEW",
                "IN_PROGRESS",
            ]:
                request_record.status = "CANCELLED"

                request_record.save(
                    update_fields=["status"]
                )

            return redirect(
                "request_detail",
                pk=request_record.pk
            )

        if handling:
            form = RequestHandlingForm(
                request.POST,
                instance=handling,
            )
        else:
            form = RequestHandlingForm(
                request.POST
            )

        if form.is_valid():

            handling = form.save(
                commit=False
            )

            handling.request = request_record
            handling.save()

            if handling.repair_result == "REPAIRED":
                request_record.status = "COMPLETED"
            else:
                request_record.status = "IN_PROGRESS"

            request_record.save(
                update_fields=["status"]
            )

            return redirect(
                "request_detail",
                pk=request_record.pk
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:
        if handling:
            form = RequestHandlingForm(
                instance=handling
            )
        else:
            form = RequestHandlingForm()

    return render(
        request,
        "core/request_detail.html",
        {
            "request_record": request_record,
            "handling": handling,
            "form": form,
        },
    )

