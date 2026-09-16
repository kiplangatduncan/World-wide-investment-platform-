document.addEventListener(
    "DOMContentLoaded",
    function () {

        const alerts = document.querySelectorAll(
            ".alert"
        );

        alerts.forEach(
            function (alert) {

                setTimeout(
                    function () {

                        alert.style.opacity = "0";

                        alert.style.transition =
                            "opacity 0.5s";

                        setTimeout(
                            function () {
                                alert.remove();
                            },
                            500
                        );

                    },
                    5000
                );

            }
        );


        const forms = document.querySelectorAll(
            "form"
        );

        forms.forEach(
            function (form) {

                form.addEventListener(
                    "submit",
                    function () {

                        const button =
                            form.querySelector(
                                "button[type='submit']"
                            );

                        if (button) {

                            button.disabled = true;

                            button.style.opacity =
                                "0.7";

                            button.innerText =
                                "Processing...";

                        }

                    }
                );

            }
        );

    }
);
