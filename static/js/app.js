document.addEventListener("DOMContentLoaded", () => {

    const flashes = document.querySelectorAll(".flash");

    flashes.forEach((flash) => {

        setTimeout(() => {

            flash.style.opacity = "0";

            flash.style.transform = "translateY(-5px)";

            flash.style.transition = "all .4s";

            setTimeout(() => {
                flash.remove();
            }, 400);

        }, 5000);

    });

});
