const sessionId = sessionStorage.getItem("session_id");

const welcomeText = document.getElementById("welcomeText");
const userDetails = document.getElementById("userDetails");
const logoutButton = document.getElementById("logoutButton");

if (!sessionId) {
    window.location.href = "login.html";
}

async function loadDashboard() {

    try {

        const response = await fetch(
            "http://127.0.0.1:5000/dashboard",
            {
                method: "GET",

                headers: {
                    "Session-ID": sessionId
                }
            }
        );

        const data = await response.json();

        if (!data.success) {
            sessionStorage.clear();
            window.location.href = "login.html";
            return;
        }

        const user = data.user;

        welcomeText.textContent =
            `Welcome, ${user.username}`;

        userDetails.textContent =
            `${user.department} • ${user.role_name}`;

    } catch (error) {

        console.error(error);

        userDetails.textContent =
            "Unable to load dashboard.";

    }
}

logoutButton.addEventListener("click", async function () {

    try {

        await fetch(
            "http://127.0.0.1:5000/logout",
            {
                method: "POST",

                headers: {
                    "Session-ID": sessionId
                }
            }
        );

    } finally {

        sessionStorage.clear();
        window.location.href = "login.html";

    }

});

loadDashboard();