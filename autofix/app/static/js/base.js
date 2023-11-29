for (const element of document.querySelectorAll(".dateinput, .datetimeinput"))
    element.setAttribute("type", "date");

const totalCost = document.querySelector('#id_total_cost');
const totalCostRealValue = totalCost.value;
if (totalCost) {
    const isWarranty = document.querySelector('#id_is_warranty');

    const onChange = () => {
        totalCost.value = isWarranty.checked ? "0.00" : totalCostRealValue;
    }

    isWarranty.addEventListener("change", onChange);
    onChange();
}

