const loginForm = document.getElementById("loginForm");
const loginMessage = document.getElementById("loginMessage");

loginForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    loginMessage.textContent = "Signing in...";

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

        if (response.ok) {

            loginMessage.textContent = "Login successful.";

            console.log("Authenticated user:", data.user);

        } else {

            loginMessage.textContent = data.message;
        }

    } catch (error) {

        console.error(error);

        loginMessage.textContent =
            "Unable to connect to the Anomex server.";
    }
});