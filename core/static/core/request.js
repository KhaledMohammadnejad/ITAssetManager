
document.addEventListener("DOMContentLoaded", function () {
    const requesterField = document.getElementById("id_requester");
    const priorityField = document.getElementById("id_priority");

    if (!requesterField || !priorityField) {
        return;
    }

    function updatePriority() {
    const selectedOption =
        requesterField.options[requesterField.selectedIndex];

    const unitName = selectedOption
        ? selectedOption.text.trim()
        : "";

    if (
        unitName === "Principal Dr. Jasem Office" ||
        unitName === "Principal Dr. Hadi Office"
    ) {
        priorityField.value = "URGENT";
        priorityField.style.pointerEvents = "none";
        priorityField.style.backgroundColor = "#eee";
    } else {
        priorityField.value = "NORMAL";
        priorityField.style.pointerEvents = "";
        priorityField.style.backgroundColor = "";
    }
}

requesterField.addEventListener("change", updatePriority);

updatePriority();
});

