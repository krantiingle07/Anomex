/* =========================================================
   ANOMEX — alerts.js
   Fetches, renders and manages anomaly alert cards.
   Connects to: GET /api/anomalies
                PATCH /api/anomalies/:id/acknowledge
                GET   /api/dashboard-stats (for stat counts)
   ========================================================= */

const API_BASE = "http://127.0.0.1:5000";

// Session guard
const sessionId = sessionStorage.getItem("session_id");
if (!sessionId) {
    window.location.href = "login.html";
}


/* ─────────────────────────────────────────────
   STATE
───────────────────────────────────────────── */

let allAlerts     = [];      // raw data from API
let activeAlertId = null;    // ID of alert currently open in modal


/* ─────────────────────────────────────────────
   DOM REFS
───────────────────────────────────────────── */

const alertsContainer  = document.getElementById("alertsContainer");
const loadingState     = document.getElementById("loadingState");
const emptyState       = document.getElementById("emptyState");
const alertResultText  = document.getElementById("alertResultText");

const severityFilter   = document.getElementById("severityFilter");
const statusFilter     = document.getElementById("statusFilter");
const searchInput      = document.getElementById("searchInput");
const refreshBtn       = document.getElementById("refreshBtn");

const totalAlertsValue = document.getElementById("totalAlertsValue");
const criticalValue    = document.getElementById("criticalValue");
const unackedValue     = document.getElementById("unackedValue");
const ackedValue       = document.getElementById("ackedValue");

const alertModal       = document.getElementById("alertModal");
const modalTitle       = document.getElementById("modalTitle");
const modalBody        = document.getElementById("modalBody");
const modalClose       = document.getElementById("modalClose");
const modalCancelBtn   = document.getElementById("modalCancelBtn");
const modalAckBtn      = document.getElementById("modalAckBtn");

const themeToggle      = document.getElementById("themeToggle");
const themeIcon        = document.getElementById("themeIcon");
const themeLabel       = document.getElementById("themeLabel");


/* ─────────────────────────────────────────────
   THEME TOGGLE
───────────────────────────────────────────── */

function applyTheme(dark) {
    document.body.classList.toggle("dark", dark);
    themeIcon.textContent  = dark ? "☀" : "☾";
    themeLabel.textContent = dark ? "Light" : "Dark";
    localStorage.setItem("anomex_theme", dark ? "dark" : "light");
}

themeToggle.addEventListener("click", () => {
    applyTheme(!document.body.classList.contains("dark"));
});

// Restore saved theme
const savedTheme = localStorage.getItem("anomex_theme");
if (savedTheme === "dark") applyTheme(true);


/* ─────────────────────────────────────────────
   API HELPERS
───────────────────────────────────────────── */

async function apiFetch(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: {
            "Content-Type": "application/json",
            "Session-ID":   sessionId,
        },
        ...options,
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text}`);
    }

    return res.json();
}


/* ─────────────────────────────────────────────
   LOAD ALERTS
───────────────────────────────────────────── */

async function loadAlerts() {
    showLoading(true);

    try {
        allAlerts = await apiFetch("/api/anomalies");
        renderAlerts();
        await loadStats();
    } catch (err) {
        console.error("Failed to load alerts:", err);
        showToast("Could not connect to backend. Is Flask running?", "danger");
        showLoading(false);
        showEmpty(true, "Backend unavailable. Check Flask server.");
    }
}


/* ─────────────────────────────────────────────
   LOAD DASHBOARD STATS
───────────────────────────────────────────── */

async function loadStats() {
    try {
        const stats = await apiFetch("/api/dashboard-stats");

        animateCount(totalAlertsValue, stats.total_anomalies   ?? 0);
        animateCount(unackedValue,     stats.unacknowledged_alerts ?? 0);

        // Calculate critical and acked from allAlerts
        const critical = allAlerts.filter(a => a.severity === "CRITICAL").length;
        const acked    = allAlerts.filter(a => a.acknowledged).length;

        animateCount(criticalValue, critical);
        animateCount(ackedValue,    acked);

    } catch (err) {
        console.warn("Stats load failed:", err);
    }
}


/* ─────────────────────────────────────────────
   FILTER & RENDER
───────────────────────────────────────────── */

function getFilteredAlerts() {
    const severity = severityFilter.value.toUpperCase();
    const status   = statusFilter.value;    // '' | 'true' | 'false'
    const query    = searchInput.value.toLowerCase().trim();

    return allAlerts.filter(alert => {

        if (severity && alert.severity !== severity) return false;

        if (status === "true"  && !alert.acknowledged) return false;
        if (status === "false" &&  alert.acknowledged) return false;

        if (query) {
            const haystack = [
                alert.description  ?? "",
                alert.query_text   ?? "",
                alert.alert_type   ?? "",
                alert.severity     ?? "",
                String(alert.user_id ?? ""),
            ].join(" ").toLowerCase();

            if (!haystack.includes(query)) return false;
        }

        return true;
    });
}


function renderAlerts() {
    const filtered = getFilteredAlerts();

    // Remove old cards (keep loading & empty state divs)
    const oldCards = alertsContainer.querySelectorAll(".alert-card");
    oldCards.forEach(c => c.remove());

    showLoading(false);

    if (filtered.length === 0) {
        showEmpty(true);
        alertResultText.textContent = "No alerts match your filters.";
        return;
    }

    showEmpty(false);
    alertResultText.textContent = `${filtered.length} alert${filtered.length !== 1 ? "s" : ""} found`;

    filtered.forEach(alert => {
        const card = buildAlertCard(alert);
        alertsContainer.appendChild(card);
    });
}


/* ─────────────────────────────────────────────
   CARD BUILDER
───────────────────────────────────────────── */

function buildAlertCard(alert) {
    const card = document.createElement("div");
    card.className = "alert-card";
    card.setAttribute("data-id", alert.alert_id);

    const severityClass = severityBadgeClass(alert.severity);
    const statusClass   = alert.acknowledged ? "status-resolved" : "status-open";
    const statusLabel   = alert.acknowledged ? "Acknowledged"    : "Open";
    const iconSymbol    = severityIcon(alert.severity);
    const timeStr       = formatDateTime(alert.detected_at);

    card.innerHTML = `
        <div class="alert-icon">${iconSymbol}</div>

        <div class="alert-content">
            <div class="alert-title">${escapeHTML(alert.alert_type || "BEHAVIORAL")} — User ${alert.user_id ?? "?"}</div>

            <p class="alert-description">
                ${escapeHTML(truncate(alert.description || "No description.", 160))}
            </p>

            <div class="alert-meta">
                <span class="severity ${severityClass}">${alert.severity}</span>
                <span class="status  ${statusClass}">${statusLabel}</span>
                <span>Score: ${fmtScore(alert.anomaly_score)}</span>
                <span>Exec: ${alert.execution_time_ms ?? "?"} ms</span>
                <span>${timeStr}</span>
            </div>
        </div>

        <div class="alert-actions">
            <button class="view-btn"  data-id="${alert.alert_id}" type="button">View</button>
            ${!alert.acknowledged
                ? `<button class="ack-btn" data-id="${alert.alert_id}" type="button">Acknowledge</button>`
                : ""}
        </div>
    `;

    card.querySelector(".view-btn").addEventListener("click", e => {
        e.stopPropagation();
        openModal(alert);
    });

    const ackBtn = card.querySelector(".ack-btn");
    if (ackBtn) {
        ackBtn.addEventListener("click", e => {
            e.stopPropagation();
            acknowledgeAlert(alert.alert_id);
        });
    }

    card.addEventListener("click", () => openModal(alert));

    return card;
}


/* ─────────────────────────────────────────────
   MODAL
───────────────────────────────────────────── */

function openModal(alert) {
    activeAlertId = alert.alert_id;

    modalTitle.textContent = `Alert #${alert.alert_id} — ${alert.alert_type || "BEHAVIORAL"}`;

    modalBody.innerHTML = `
        <div class="modal-detail-row">
            <span class="modal-detail-label">Severity</span>
            <span class="modal-detail-value">
                <span class="severity ${severityBadgeClass(alert.severity)}">${alert.severity}</span>
            </span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Status</span>
            <span class="modal-detail-value">
                <span class="status ${alert.acknowledged ? 'status-resolved' : 'status-open'}">
                    ${alert.acknowledged ? "Acknowledged" : "Open"}
                </span>
            </span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Anomaly Score</span>
            <span class="modal-detail-value">${fmtScore(alert.anomaly_score)}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">User ID</span>
            <span class="modal-detail-value">${alert.user_id ?? "—"}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Query Status</span>
            <span class="modal-detail-value">${escapeHTML(alert.status ?? "—")}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Execution Time</span>
            <span class="modal-detail-value">${alert.execution_time_ms ?? "—"} ms</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Detected At</span>
            <span class="modal-detail-value">${formatDateTime(alert.detected_at)}</span>
        </div>
        <div class="modal-detail-row">
            <span class="modal-detail-label">Description</span>
            <span class="modal-detail-value">${escapeHTML(alert.description ?? "—")}</span>
        </div>
        <div class="modal-query-box">${escapeHTML(alert.query_text ?? "No query text available.")}</div>
    `;

    // Update ack button state
    modalAckBtn.disabled      = !!alert.acknowledged;
    modalAckBtn.textContent   = alert.acknowledged ? "Already Acknowledged" : "Acknowledge Alert";

    alertModal.classList.add("show");
    document.body.style.overflow = "hidden";
}

function closeModal() {
    alertModal.classList.remove("show");
    document.body.style.overflow = "";
    activeAlertId = null;
}

modalClose.addEventListener("click",      closeModal);
modalCancelBtn.addEventListener("click",  closeModal);

alertModal.addEventListener("click", e => {
    if (e.target === alertModal) closeModal();
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
});

modalAckBtn.addEventListener("click", () => {
    if (activeAlertId) acknowledgeAlert(activeAlertId);
});


/* ─────────────────────────────────────────────
   ACKNOWLEDGE
───────────────────────────────────────────── */

async function acknowledgeAlert(alertId) {
    try {
        await apiFetch(`/api/anomalies/${alertId}/acknowledge`, { method: "PATCH" });

        // Update local state
        const idx = allAlerts.findIndex(a => a.alert_id === alertId);
        if (idx !== -1) allAlerts[idx].acknowledged = true;

        renderAlerts();
        await loadStats();
        closeModal();
        showToast("Alert acknowledged successfully.");

    } catch (err) {
        console.error("Acknowledge failed:", err);
        showToast("Failed to acknowledge alert.", "danger");
    }
}


/* ─────────────────────────────────────────────
   FILTER EVENTS
───────────────────────────────────────────── */

severityFilter.addEventListener("change", renderAlerts);
statusFilter.addEventListener("change",   renderAlerts);
searchInput.addEventListener("input",     renderAlerts);

refreshBtn.addEventListener("click", () => {
    loadAlerts();
    showToast("Refreshing alerts…");
});


/* ─────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────── */

function showLoading(show) {
    loadingState.style.display = show ? "flex" : "none";
}

function showEmpty(show, msg) {
    emptyState.style.display = show ? "block" : "none";
    if (msg) emptyState.querySelector("p").textContent = msg;
}

function escapeHTML(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function truncate(str, max) {
    return str.length > max ? str.slice(0, max) + "…" : str;
}

function fmtScore(score) {
    if (score == null) return "—";
    return parseFloat(score).toFixed(3);
}

function formatDateTime(isoStr) {
    if (!isoStr) return "—";
    try {
        const d = new Date(isoStr);
        return d.toLocaleString("en-IN", { hour12: false });
    } catch {
        return isoStr;
    }
}

function severityBadgeClass(sev) {
    const map = {
        CRITICAL: "severity-critical",
        HIGH:     "severity-high",
        MEDIUM:   "severity-medium",
        LOW:      "severity-low",
    };
    return map[(sev || "").toUpperCase()] || "severity-low";
}

function severityIcon(sev) {
    const map = {
        CRITICAL: "✕",
        HIGH:     "!",
        MEDIUM:   "◇",
        LOW:      "·",
    };
    return map[(sev || "").toUpperCase()] || "◇";
}

function animateCount(el, target) {
    const start = parseInt(el.textContent) || 0;
    const diff  = target - start;
    const steps = 20;
    let   step  = 0;

    const timer = setInterval(() => {
        step++;
        el.textContent = Math.round(start + (diff * step) / steps);
        if (step >= steps) {
            clearInterval(timer);
            el.textContent = target;
        }
    }, 18);
}

let toastTimer = null;

function showToast(message, type = "success") {
    let toast = document.getElementById("anomexToast");

    if (!toast) {
        toast = document.createElement("div");
        toast.id        = "anomexToast";
        toast.className = "toast";
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className   = `toast${type === "danger" ? " danger" : ""}`;

    requestAnimationFrame(() => {
        toast.classList.add("show");
    });

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}


/* ─────────────────────────────────────────────
   INIT
───────────────────────────────────────────── */

loadAlerts();
