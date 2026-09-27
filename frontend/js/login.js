const loginForm = document.getElementById("loginForm");
const loginButton = document.getElementById("loginButton");
const loginMessage = document.getElementById("loginMessage");

loginForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    loginMessage.textContent = "";
    loginMessage.className = "login-message";

    loginButton.disabled = true;
    loginButton.textContent = "Signing in...";

    try {

        const response = await fetch("http://127.0.0.1:5000/login", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {

            loginMessage.textContent = "Login successful.";
            loginMessage.classList.add("success");

            /*
             * Temporary storage for development.
             * We will replace this with a proper session mechanism later.
             */
            sessionStorage.setItem("session_id", data.session_id);
            sessionStorage.setItem("user_id", data.user_id);
            sessionStorage.setItem("username", data.username);

            setTimeout(() => {
                window.location.href = "dashboard.html";
            }, 500);

        } else {

            loginMessage.textContent = data.message;
            loginMessage.classList.add("error");

        }

    } catch (error) {

        console.error(error);

        loginMessage.textContent =
            "Unable to connect to the Anomex server.";

        loginMessage.classList.add("error");

    } finally {

        loginButton.disabled = false;
        loginButton.textContent = "Sign In";

    }
});

// Password visibility toggle
const passwordInput = document.getElementById("password");
const passwordToggle = document.getElementById("passwordToggle");

passwordToggle.addEventListener("click", function () {

    if (passwordInput.type === "password") {

        passwordInput.type = "text";

        passwordToggle.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"></path>
                <circle cx="12" cy="12" r="3"></circle>
            </svg>
        `;

    } else {

        passwordInput.type = "password";

        passwordToggle.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 3l18 18"></path>
                <path d="M10.6 5.2A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a18.7 18.7 0 0 1-3.1 3.9"></path>
                <path d="M6.1 6.1C3.5 7.8 2 12 2 12s3.5 7 10 7c1.4 0 2.7-.3 3.8-.8"></path>
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"></path>
            </svg>
        `;

    }

});