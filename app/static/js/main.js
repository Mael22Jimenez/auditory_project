
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    const submitButton = form?.querySelector("button");

    if (form && submitButton) {
        form.addEventListener("submit", function () {
            // Evitar que se presione varias veces
            submitButton.disabled = true;

            // Feedback visual
            submitButton.innerText = "Procesando...";
        });
    }
});
