
document.addEventListener("DOMContentLoaded", function () {

    const repairResult = document.getElementById("id_repair_result");
    const nextAction = document.getElementById("id_next_action");
    const asset = document.getElementById("id_asset");
    const warrantyStatus = document.getElementById("id_warranty_status");

    const workshopResult =
        document.getElementById("id_workshop_result");

    const externalApproval =
        document.getElementById("id_external_approval");

    const externalRepairResult =
        document.getElementById("id_external_repair_result");

    const replacementAsset =
        document.getElementById("id_replacement_asset");

    const replacementType =
        document.getElementById("id_replacement_type");


    function updateFields() {

        const result = repairResult.value;


        // Update Warranty Status from the selected Asset.
        const selectedAsset = asset.options[asset.selectedIndex];

        if (
            selectedAsset &&
            selectedAsset.dataset.warrantyStatus
        ) {
            warrantyStatus.value =
                selectedAsset.dataset.warrantyStatus;
        } else {
            warrantyStatus.value = "";
        }


        // Check whether further action is required.
        const needsFurtherAction =
            result === "FURTHER_ACTION" ||
            result === "NOT_REPAIRED";


        // If no further action is required,
        // set Next Action to None / Finished.
        if (!needsFurtherAction) {
            nextAction.value = "NONE";
        }


        // Get the current Next Action.
        const action = nextAction.value;


        // Next Action
        nextAction.disabled = !needsFurtherAction;


        // IT Workshop
        const isWorkshop =
            needsFurtherAction && action === "WORKSHOP";

        workshopResult.disabled = !isWorkshop;


        // External Repair
        // External repair can be selected directly,
        // or can result from the Workshop.
        const isExternal =
            needsFurtherAction &&
            (
                action === "EXTERNAL" ||
                (
                    action === "WORKSHOP" &&
                    workshopResult.value === "EXTERNAL_REPAIR"
                )
            );

        externalRepairResult.disabled = !isExternal;


        /*
         * External Approval
         *
         * Valid warranty:
         *     Approval is NOT required.
         *
         * Expired / No Warranty:
         *     Principal approval is required.
         */
        if (isExternal) {

            if (warrantyStatus.value === "Valid") {

                externalApproval.value = "NOT_REQUIRED";
                externalApproval.disabled = true;

            } else if (
                warrantyStatus.value === "Expired" ||
                warrantyStatus.value === "No Warranty"
            ) {

                externalApproval.disabled = false;

            } else {

                externalApproval.value = "NOT_REQUIRED";
                externalApproval.disabled = true;
            }

        } else {

            externalApproval.value = "NOT_REQUIRED";
            externalApproval.disabled = true;
        }


        // Replacement
        // Replacement
        const isReplacement =
            needsFurtherAction &&
        (
            action === "REPLACEMENT" ||
            (
                action === "WORKSHOP" &&
                workshopResult.value === "REPLACEMENT"
            )
    );

        replacementAsset.disabled = !isReplacement;
        replacementType.disabled = !isReplacement;


        // Clear fields that are not currently relevant.

        if (!isWorkshop) {
            workshopResult.value = "";
        }

        if (!isExternal) {
            externalRepairResult.value = "";
        }

        if (!isReplacement) {
            replacementAsset.value = "";
            replacementType.value = "";
        }
    }


    // Repair Result changes.
    repairResult.addEventListener(
        "change",
        updateFields
    );


    // Next Action changes.
    nextAction.addEventListener(
        "change",
        updateFields
    );


    // Workshop Result changes.
    workshopResult.addEventListener(
        "change",
        updateFields
    );


    // Asset changes.
    asset.addEventListener(
        "change",
        updateFields
    );


    // Apply correct state when the page loads.
    updateFields();

});

