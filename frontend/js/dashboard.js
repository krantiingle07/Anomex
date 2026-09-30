const API_BASE = "http://127.0.0.1:5000";

const sessionId = sessionStorage.getItem("session_id");

if (!sessionId) {
    window.location.href = "login.html";
}


/* =============================
   DOM ELEMENTS
============================= */

const logoutButton =
    document.getElementById("logoutButton");

const profileLogoutButton =
    document.getElementById("profileLogoutButton");

const refreshButton =
    document.getElementById("refreshButton");

const notificationButton =
    document.getElementById("notificationButton");

const userProfileButton =
    document.getElementById("userProfileButton");

const profileCard =
    document.getElementById("profileCard");

const sidebarUsername =
    document.getElementById("sidebarUsername");

const sidebarRole =
    document.getElementById("sidebarRole");

const topbarUsername =
    document.getElementById("topbarUsername");

const topbarDepartment =
    document.getElementById("topbarDepartment");

const sidebarAvatar =
    document.getElementById("sidebarAvatar");

const topbarAvatar =
    document.getElementById("topbarAvatar");

const pageTitle =
    document.getElementById("pageTitle");

const notificationCount =
    document.getElementById("notificationCount");

const mobileMenuButton =
    document.getElementById("mobileMenuButton");

const sidebar =
    document.getElementById("sidebar");

const mobileOverlay =
    document.getElementById("mobileOverlay");


/* =============================
   SESSION
============================= */

function clearSession() {

    sessionStorage.removeItem("session_id");
    sessionStorage.removeItem("user_id");
    sessionStorage.removeItem("username");

}


/* =============================
   API HELPER
============================= */

async function fetchAPI(endpoint) {

    const response = await fetch(
        `${API_BASE}${endpoint}`,
        {
            method: "GET",

            headers: {
                "Session-ID": sessionId
            }
        }
    );

    if (!response.ok) {
        throw new Error(
            `API request failed: ${response.status}`
        );
    }

    return await response.json();
}


/* =============================
   VERIFY LOGIN SESSION
============================= */

async function verifySession() {

    try {

        const response = await fetch(
            `${API_BASE}/dashboard`,
            {
                method: "GET",

                headers: {
                    "Session-ID": sessionId
                }
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success || !data.user) {

            clearSession();

            window.location.href = "login.html";

            return null;
        }

        return data.user;

    } catch (error) {

        console.error(
            "Session verification failed:",
            error
        );

        clearSession();

        window.location.href = "login.html";

        return null;
    }
}


/* =============================
   DISPLAY USER
============================= */

function displayUser(user) {

    const username =
        user.username || "User";

    const department =
        user.department || "Unknown Department";

    const role =
        user.role_name || "Unknown Role";

    const userId =
        user.user_id ?? "—";

    const avatarLetter =
        username.charAt(0).toUpperCase();


    /* Sidebar */

    sidebarUsername.textContent =
        username;

    sidebarRole.textContent =
        role;

    sidebarAvatar.textContent =
        avatarLetter;


    /* Topbar */

    topbarUsername.textContent =
        username;

    topbarDepartment.textContent =
        department;

    topbarAvatar.textContent =
        avatarLetter;


    /* Profile Card */

    document.getElementById(
        "profileAvatar"
    ).textContent = avatarLetter;

    document.getElementById(
        "profileUsername"
    ).textContent = username;

    document.getElementById(
        "profileRole"
    ).textContent = role;

    document.getElementById(
        "profileDepartment"
    ).textContent = department;

    document.getElementById(
        "profileUserId"
    ).textContent = userId;

    document.getElementById(
        "profileRoleDetail"
    ).textContent = role;
}


/* =============================
   FORMATTING
============================= */

function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function truncateText(
    value,
    length = 70
) {

    if (!value) {
        return "—";
    }

    if (value.length <= length) {
        return value;
    }

    return `${value.substring(0, length)}...`;
}


function formatDate(value) {

    if (!value) {
        return "—";
    }

    const date =
        new Date(value);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return value;
    }

    return date.toLocaleString();
}


function statusClass(status) {

    if (!status) {
        return "";
    }

    return status.toLowerCase();
}


function severityClass(severity) {

    if (!severity) {
        return "";
    }

    return severity.toLowerCase();
}


/* =============================
   DASHBOARD STATISTICS
============================= */

function updateStatistics(
    queryLogs,
    anomalies,
    users
) {

    const successful =
        queryLogs.filter(
            log => log.status === "SUCCESS"
        ).length;

    const failed =
        queryLogs.filter(
            log => log.status === "FAILURE"
        ).length;

    const blocked =
        queryLogs.filter(
            log => log.status === "BLOCKED"
        ).length;

    const unacknowledged =
        anomalies.filter(
            alert => !alert.acknowledged
        ).length;


    document.getElementById(
        "totalQueries"
    ).textContent =
        queryLogs.length;


    document.getElementById(
        "totalAnomalies"
    ).textContent =
        anomalies.length;


    document.getElementById(
        "totalAlerts"
    ).textContent =
        unacknowledged;


    document.getElementById(
        "totalUsers"
    ).textContent =
        users.length;


    document.getElementById(
        "successfulQueries"
    ).textContent =
        successful;


    document.getElementById(
        "failedQueries"
    ).textContent =
        failed;


    document.getElementById(
        "blockedQueries"
    ).textContent =
        blocked;


    notificationCount.textContent =
        unacknowledged;
}


/* =============================
   OVERVIEW QUERY TABLE
============================= */

function renderOverviewQueries(
    queryLogs
) {

    const table =
        document.getElementById(
            "overviewQueryTable"
        );

    const recent =
        queryLogs.slice(0, 6);


    if (!recent.length) {

        table.innerHTML = `
            <tr>
                <td colspan="4" class="table-empty">
                    No query activity available.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        recent.map(log => `

            <tr>

                <td class="query-cell">
                    ${escapeHTML(
                        truncateText(
                            log.query_text
                        )
                    )}
                </td>

                <td>
                    ${escapeHTML(
                        log.resource || "—"
                    )}
                </td>

                <td>

                    <span class="status-badge ${statusClass(
                        log.status
                    )}">

                        ${escapeHTML(
                            log.status || "UNKNOWN"
                        )}

                    </span>

                </td>

                <td>
                    ${log.execution_time_ms ?? "—"} ms
                </td>

            </tr>

        `).join("");
}


/* =============================
   QUERY TABLE
============================= */

function renderQueryTable(
    queryLogs
) {

    const table =
        document.getElementById(
            "queryTable"
        );


    if (!queryLogs.length) {

        table.innerHTML = `
            <tr>
                <td colspan="7" class="table-empty">
                    No query logs available.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        queryLogs.map(log => `

            <tr>

                <td>
                    ${log.log_id ?? "—"}
                </td>

                <td>
                    ${log.user_id ?? "—"}
                </td>

                <td class="query-cell">
                    ${escapeHTML(
                        truncateText(
                            log.query_text,
                            100
                        )
                    )}
                </td>

                <td>
                    ${escapeHTML(
                        log.resource || "—"
                    )}
                </td>

                <td>
                    ${log.execution_time_ms ?? "—"} ms
                </td>

                <td>

                    <span class="status-badge ${statusClass(
                        log.status
                    )}">

                        ${escapeHTML(
                            log.status || "UNKNOWN"
                        )}

                    </span>

                </td>

                <td>
                    ${formatDate(log.timestamp)}
                </td>

            </tr>

        `).join("");
}


/* =============================
   RECENT ANOMALIES
============================= */

function renderRecentAnomalies(
    anomalies
) {

    const container =
        document.getElementById(
            "recentAnomalies"
        );

    const recent =
        anomalies.slice(0, 5);


    if (!recent.length) {

        container.innerHTML = `
            <div class="empty-state">
                No anomalies detected.
            </div>
        `;

        return;
    }


    container.innerHTML =
        recent.map(alert => `

            <div class="anomaly-item">

                <div
                    class="anomaly-indicator ${severityClass(
                        alert.severity
                    )}"
                ></div>

                <div class="anomaly-content">

                    <strong>
                        ${escapeHTML(
                            alert.alert_type ||
                            "Anomaly"
                        )}
                    </strong>

                    <span>
                        ${escapeHTML(
                            truncateText(
                                alert.description,
                                90
                            )
                        )}
                    </span>

                    <small>
                        ${formatDate(
                            alert.detected_at
                        )}
                    </small>

                </div>

                <span
                    class="severity-badge ${severityClass(
                        alert.severity
                    )}"
                >
                    ${escapeHTML(
                        alert.severity ||
                        "UNKNOWN"
                    )}
                </span>

            </div>

        `).join("");
}


/* =============================
   ANOMALY TABLE
============================= */

function renderAnomalyTable(
    anomalies
) {

    const table =
        document.getElementById(
            "anomalyTable"
        );


    if (!anomalies.length) {

        table.innerHTML = `
            <tr>
                <td colspan="7" class="table-empty">
                    No anomaly alerts available.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        anomalies.map(alert => `

            <tr>

                <td>
                    ${alert.alert_id ?? "—"}
                </td>

                <td>
                    ${alert.log_id ?? "—"}
                </td>

                <td>
                    ${escapeHTML(
                        alert.alert_type || "—"
                    )}
                </td>

                <td>

                    <span
                        class="severity-badge ${severityClass(
                            alert.severity
                        )}"
                    >
                        ${escapeHTML(
                            alert.severity ||
                            "UNKNOWN"
                        )}
                    </span>

                </td>

                <td>
                    ${alert.anomaly_score ?? "—"}
                </td>

                <td class="query-cell">
                    ${escapeHTML(
                        truncateText(
                            alert.description,
                            100
                        )
                    )}
                </td>

                <td>
                    ${formatDate(
                        alert.detected_at
                    )}
                </td>

            </tr>

        `).join("");
}


/* =============================
   SECURITY ALERTS
============================= */

function renderAlerts(
    anomalies
) {

    const container =
        document.getElementById(
            "alertList"
        );


    if (!anomalies.length) {

        container.innerHTML = `
            <div class="empty-state">
                No security alerts available.
            </div>
        `;

        return;
    }


    container.innerHTML =
        anomalies.map(alert => `

            <div class="alert-item">

                <div class="alert-icon">
                    !
                </div>

                <div class="alert-content">

                    <div class="alert-heading">

                        <strong>
                            ${escapeHTML(
                                alert.alert_type ||
                                "Security Alert"
                            )}
                        </strong>

                        <span
                            class="severity-badge ${severityClass(
                                alert.severity
                            )}"
                        >
                            ${escapeHTML(
                                alert.severity ||
                                "UNKNOWN"
                            )}
                        </span>

                    </div>

                    <p>
                        ${escapeHTML(
                            alert.description ||
                            "No description"
                        )}
                    </p>

                    <small>
                        Detected
                        ${formatDate(
                            alert.detected_at
                        )}
                    </small>

                </div>

            </div>

        `).join("");
}


/* =============================
   RECENT QUERIES
============================= */

function renderRecentQueries(
    queryLogs
) {

    const container =
        document.getElementById(
            "recentQueries"
        );

    const recent =
        queryLogs.slice(0, 5);


    if (!recent.length) {

        container.innerHTML = `
            <div class="empty-state">
                No recent queries.
            </div>
        `;

        return;
    }


    container.innerHTML =
        recent.map(log => `

            <div class="recent-query-item">

                <div>

                    <strong>
                        ${escapeHTML(
                            truncateText(
                                log.query_text,
                                55
                            )
                        )}
                    </strong>

                    <span>
                        ${escapeHTML(
                            log.resource ||
                            "Unknown resource"
                        )}
                    </span>

                </div>


                <div class="recent-query-meta">

                    <span
                        class="status-badge ${statusClass(
                            log.status
                        )}"
                    >
                        ${escapeHTML(
                            log.status ||
                            "UNKNOWN"
                        )}
                    </span>

                    <small>
                        ${formatDate(
                            log.timestamp
                        )}
                    </small>

                </div>

            </div>

        `).join("");
}


/* =============================
   USERS
============================= */

function renderUsers(users) {

    const table =
        document.getElementById(
            "userTable"
        );


    if (!users.length) {

        table.innerHTML = `
            <tr>
                <td colspan="5" class="table-empty">
                    No users available.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        users.map(user => `

            <tr>

                <td>
                    ${user.user_id ?? "—"}
                </td>

                <td>
                    <strong>
                        ${escapeHTML(
                            user.username || "—"
                        )}
                    </strong>
                </td>

                <td>
                    ${escapeHTML(
                        user.department || "—"
                    )}
                </td>

                <td>

                    <span
                        class="status-badge ${
                            user.is_active
                                ? "success"
                                : "failure"
                        }"
                    >
                        ${
                            user.is_active
                                ? "ACTIVE"
                                : "INACTIVE"
                        }
                    </span>

                </td>

                <td>
                    ${escapeHTML(
                        user.role_name || "—"
                    )}
                </td>

            </tr>

        `).join("");
}


/* =============================
   ROLES
============================= */

function renderRoles(roles) {

    const table =
        document.getElementById(
            "roleTable"
        );


    if (!roles.length) {

        table.innerHTML = `
            <tr>
                <td colspan="3" class="table-empty">
                    No roles available.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML =
        roles.map(role => `

            <tr>

                <td>
                    ${role.role_id ?? "—"}
                </td>

                <td>
                    <strong>
                        ${escapeHTML(
                            role.role_name || "—"
                        )}
                    </strong>
                </td>

                <td>

                    <span class="permission-level">
                        ${escapeHTML(
                            String(
                                role.permission_level ??
                                "—"
                            )
                        )}
                    </span>

                </td>

            </tr>

        `).join("");
}


/* =============================
   LOAD DASHBOARD
============================= */

async function loadDashboard() {

    try {

        const [
            queryLogs,
            anomalies,
            users,
            roles
        ] = await Promise.all([

            fetchAPI(
                "/api/query-logs"
            ),

            fetchAPI(
                "/api/anomalies"
            ),

            fetchAPI(
                "/api/users"
            ),

            fetchAPI(
                "/api/roles"
            )

        ]);


        updateStatistics(
            queryLogs,
            anomalies,
            users
        );


        renderOverviewQueries(
            queryLogs
        );

        renderQueryTable(
            queryLogs
        );


        renderRecentAnomalies(
            anomalies
        );

        renderAnomalyTable(
            anomalies
        );


        renderAlerts(
            anomalies
        );


        renderRecentQueries(
            queryLogs
        );


        renderUsers(
            users
        );


        renderRoles(
            roles
        );


    } catch (error) {

        console.error(
            "Dashboard loading error:",
            error
        );

    }
}


/* =============================
   SECTION NAVIGATION
============================= */

function openSection(
    sectionName
) {

    const sections =
        document.querySelectorAll(
            ".dashboard-section"
        );

    const navItems =
        document.querySelectorAll(
            ".nav-item"
        );


    sections.forEach(
        section => {
            section.classList.remove(
                "active"
            );
        }
    );


    navItems.forEach(
        item => {
            item.classList.remove(
                "active"
            );
        }
    );


    const section =
        document.getElementById(
            `section-${sectionName}`
        );


    const navItem =
        document.querySelector(
            `.nav-item[data-section="${sectionName}"]`
        );


    if (section) {

        section.classList.add(
            "active"
        );

    }


    if (navItem) {

        navItem.classList.add(
            "active"
        );

    }


    const titles = {

        overview: "Overview",

        queries:
            "Query Monitoring",

        anomalies:
            "Anomaly Detection",

        alerts:
            "Security Alerts",

        users:
            "Users",

        roles:
            "Roles",

        audit:
            "Audit Logs",

        settings:
            "Settings"

    };


    pageTitle.textContent =
        titles[sectionName] ||
        "Overview";


    closeMobileSidebar();
}


/* =============================
   SIDEBAR NAVIGATION
============================= */

document
    .querySelectorAll(".nav-item")
    .forEach(item => {

        item.addEventListener(
            "click",
            function () {

                openSection(
                    this.dataset.section
                );

            }
        );

    });


/* =============================
   DASHBOARD "VIEW ALL" BUTTONS
============================= */

document
    .querySelectorAll(
        "[data-section-target]"
    )
    .forEach(button => {

        button.addEventListener(
            "click",
            function () {

                openSection(
                    this.dataset.sectionTarget
                );

            }
        );

    });


/* =============================
   SECURITY ALERT BUTTON
============================= */

if (notificationButton) {

    notificationButton.addEventListener(
        "click",
        function () {

            openSection(
                "alerts"
            );

        }
    );

}


/* =============================
   USER PROFILE CARD
============================= */

if (userProfileButton) {

    userProfileButton.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            profileCard.classList.toggle(
                "open"
            );

        }
    );

}


if (profileCard) {

    profileCard.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

        }
    );

}


document.addEventListener(
    "click",
    function () {

        if (profileCard) {

            profileCard.classList.remove(
                "open"
            );

        }

    }
);


/* =============================
   MOBILE SIDEBAR
============================= */

function openMobileSidebar() {

    sidebar.classList.add(
        "open"
    );

    mobileOverlay.classList.add(
        "active"
    );

}


function closeMobileSidebar() {

    sidebar.classList.remove(
        "open"
    );

    mobileOverlay.classList.remove(
        "active"
    );

}


mobileMenuButton.addEventListener(
    "click",
    openMobileSidebar
);


mobileOverlay.addEventListener(
    "click",
    closeMobileSidebar
);


/* =============================
   REFRESH
============================= */

refreshButton.addEventListener(
    "click",
    async function () {

        refreshButton.classList.add(
            "rotating"
        );

        await loadDashboard();

        setTimeout(
            () => {

                refreshButton.classList.remove(
                    "rotating"
                );

            },
            500
        );

    }
);


/* =============================
   LOGOUT
============================= */

async function logout() {

    try {

        await fetch(
            `${API_BASE}/logout`,
            {
                method: "POST",

                headers: {
                    "Session-ID": sessionId
                }
            }
        );

    } catch (error) {

        console.error(
            "Logout error:",
            error
        );

    } finally {

        clearSession();

        window.location.href =
            "index.html";

    }
}


logoutButton.addEventListener(
    "click",
    logout
);


profileLogoutButton.addEventListener(
    "click",
    logout
);


/* =============================
   INITIALIZE
============================= */

async function initializeDashboard() {

    const user =
        await verifySession();


    if (!user) {
        return;
    }


    displayUser(
        user
    );


    await loadDashboard();

}


initializeDashboard();