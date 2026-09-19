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