// For Filters
document.addEventListener("DOMContentLoaded", function () {
    var filterBtn = document.getElementById("filter-btn");
    var btnTxt = document.getElementById("btn-txt");
    var filterAngle = document.getElementById("filter-angle");

    $("#filterbar").collapse(false);
    var count = 0;
    function changeBtnTxt() {
        $("#filterbar").collapse(true);
        count++;
        if (count % 2 != 0) {
            filterAngle.classList.add("fa-angle-right");
            btnTxt.innerText = "show filters";
            filterBtn.style.backgroundColor = "#36a31b";
        } else {
            filterAngle.classList.remove("fa-angle-right");
            btnTxt.innerText = "hide filters";
            filterBtn.style.backgroundColor = "#ff935d";
        }
    }
    filterBtn.addEventListener("click", changeBtnTxt);

    // For Applying Filters
    $("#inner-box").collapse(false);
    $("#inner-box2").collapse(false);

    // For changing NavBar-Toggler-Icon
    var icon = document.getElementById("icon");
    var myNav = document.getElementById("mynav");
    var count2 = 0;

    function changeIcon() {
        count2++;
        if (count2 % 2 != 0) {
            // Show the close icon and expand the menu
            icon.innerHTML = '<span class="far fa-times-circle" style="width:100%"></span>';
            icon.style.paddingTop = "5px";
            icon.style.paddingBottom = "5px";
            icon.style.fontSize = "1.8rem";
            myNav.classList.add("show");
        } else {
            // Show the default icon and collapse the menu
            icon.innerHTML = '<span class="navbar-toggler-icon"></span>';
            icon.style.paddingTop = "5px";
            icon.style.paddingBottom = "5px";
            icon.style.fontSize = "1.2rem";
            myNav.classList.remove("show");
        }
    }
    icon.addEventListener("click", changeIcon);


    // For Range Sliders
    var inputLeft = document.getElementById("input-left");
    var inputRight = document.getElementById("input-right");

    var thumbLeft = document.querySelector(".slider > .thumb.left");
    var thumbRight = document.querySelector(".slider > .thumb.right");
    var range = document.querySelector(".slider > .range");

    var amountLeft = document.getElementById("amount-left");
    var amountRight = document.getElementById("amount-right");

    function setLeftValue() {
        var _this = inputLeft,
            min = parseInt(_this.min),
            max = parseInt(_this.max);

        _this.value = Math.min(
            parseInt(_this.value),
            parseInt(inputRight.value) - 1
        );

        var percent = ((_this.value - min) / (max - min)) * 100;

        thumbLeft.style.left = percent + "%";
        range.style.left = percent + "%";
        amountLeft.innerText = parseInt(percent * 100);
    }
    setLeftValue();

    function setRightValue() {
        var _this = inputRight,
            min = parseInt(_this.min),
            max = parseInt(_this.max);

        _this.value = Math.max(
            parseInt(_this.value),
            parseInt(inputLeft.value) + 1
        );

        var percent = ((_this.value - min) / (max - min)) * 100;

        amountRight.innerText = parseInt(percent * 100);
        thumbRight.style.right = 100 - percent + "%";
        range.style.right = 100 - percent + "%";
    }
    setRightValue();

    inputLeft.addEventListener("input", setLeftValue);
    inputRight.addEventListener("input", setRightValue);

    inputLeft.addEventListener("mouseover", function () {
        thumbLeft.classList.add("hover");
    });
    inputLeft.addEventListener("mouseout", function () {
        thumbLeft.classList.remove("hover");
    });
    inputLeft.addEventListener("mousedown", function () {
        thumbLeft.classList.add("active");
    });
    inputLeft.addEventListener("mouseup", function () {
        thumbLeft.classList.remove("active");
    });

    inputRight.addEventListener("mouseover", function () {
        thumbRight.classList.add("hover");
    });
    inputRight.addEventListener("mouseout", function () {
        thumbRight.classList.remove("hover");
    });
    inputRight.addEventListener("mousedown", function () {
        thumbRight.classList.add("active");
    });
    inputRight.addEventListener("mouseup", function () {
        thumbRight.classList.remove("active");
    });
});

// Function to toggle all checkboxes
function toggleAllCheckboxes(selectAllCheckbox) {
    const checkboxes = document.querySelectorAll(
        '#inner-box .individual-checkbox input[type="checkbox"]'
    );
    checkboxes.forEach((checkbox) => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}
// Function to check the state of individual checkboxes
function checkIndividualCheckboxes() {
    const checkboxes = document.querySelectorAll(
        '#inner-box .individual-checkbox input[type="checkbox"]'
    );
    const selectAllCheckbox = document.getElementById("selectAll");

    const allChecked = Array.from(checkboxes).every(
        (checkbox) => checkbox.checked
    );
    selectAllCheckbox.checked = allChecked;
}

const individualCheckboxes = document.querySelectorAll(
    '#inner-box .individual-checkbox input[type="checkbox"]'
);
individualCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", checkIndividualCheckboxes);
});

function outerFilter() {
    const innerBox = document.getElementById("inner-box");
    const button = document.getElementById("out");
    const icon = button.querySelector("span");

    const isNotExpanded = button.getAttribute("aria-expanded") === "false";

    if (isNotExpanded) {
        innerBox.classList.remove("show");
        button.setAttribute("aria-expanded", "false");
        icon.classList.replace("fa-minus", "fa-plus");
    } else {
        innerBox.classList.add("show");
        button.setAttribute("aria-expanded", "true");
        icon.classList.replace("fa-plus", "fa-minus");
    }
}

function outerFilter2() {
    const innerBox = document.getElementById("member-count");
    const button = document.getElementById("num_out");
    const icon = button.querySelector("span");

    const isNotExpanded = button.getAttribute("aria-expanded") === "false";

    if (isNotExpanded) {
        innerBox.classList.remove("show");
        button.setAttribute("aria-expanded", "false");
        icon.classList.replace("fa-minus", "fa-plus");
    } else {
        innerBox.classList.add("show");
        button.setAttribute("aria-expanded", "true");
        icon.classList.replace("fa-plus", "fa-minus");
    }
}
