
document.addEventListener("DOMContentLoaded", function () {

    const categoryField = document.getElementById("id_category");

    if (!categoryField) {
        return;
    }

    function updateSpecificationDefinitions() {

        const selectedOption =
            categoryField.options[categoryField.selectedIndex];

        if (!selectedOption) {
            return;
        }

        let specifications = [];

        if (selectedOption.dataset.specifications) {
            specifications = JSON.parse(
                selectedOption.dataset.specifications
            );
        }

        const definitionFields = document.querySelectorAll(
            'select[name$="-definition"]'
        );

        definitionFields.forEach(function (field) {

            const currentValue = field.value;

            field.innerHTML = "";

            const emptyOption =
                document.createElement("option");

            emptyOption.value = "";
            emptyOption.textContent = "---------";

            field.appendChild(emptyOption);

            specifications.forEach(function (specification) {

                const option =
                    document.createElement("option");

                option.value = specification.id;
                option.textContent = specification.name;

                if (String(specification.id) === currentValue) {
                    option.selected = true;
                }

                field.appendChild(option);
            });
        });
    }

    categoryField.addEventListener(
        "change",
        updateSpecificationDefinitions
    );
});