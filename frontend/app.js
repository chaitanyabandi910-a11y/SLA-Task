// =========================================================
// API CONFIGURATION
// =========================================================

const API_BASE_URL = "http://127.0.0.1:8000";


// =========================================================
// DOM ELEMENTS
// =========================================================

const statsToggle = document.getElementById("statsToggle");
const statsContent = document.getElementById("statsContent");
const toggleIcon = document.getElementById("toggleIcon");

const totalServices = document.getElementById("totalServices");
const overallAvailability = document.getElementById("overallAvailability");
const slaTarget = document.getElementById("slaTarget");
const overallStatus = document.getElementById("overallStatus");
const failedSlots = document.getElementById("failedSlots");
const missingSlots = document.getElementById("missingSlots");

const servicesTable = document.getElementById("servicesTable");
const logsTable = document.getElementById("logsTable");

const logCount = document.getElementById("logCount");

const startDate = document.getElementById("startDate");
const endDate = document.getElementById("endDate");

const serviceFilter = document.getElementById("serviceFilter");

const logLimit = document.getElementById("logLimit");

const applyFilters = document.getElementById("applyFilters");
const clearFilters = document.getElementById("clearFilters");

const systemStatus = document.getElementById("systemStatus");
const statusIndicator = document.getElementById("statusIndicator");

const csvFile = document.getElementById("csvFile");
const uploadButton = document.getElementById("uploadButton");
const uploadMessage = document.getElementById("uploadMessage");


// =========================================================
// COLLAPSIBLE STATISTICS
// =========================================================

statsToggle.addEventListener("click", () => {

    const isHidden =
        statsContent.style.display === "none";

    if (isHidden) {

        statsContent.style.display = "block";

        toggleIcon.textContent = "▲";

    } else {

        statsContent.style.display = "none";

        toggleIcon.textContent = "▼";
    }

});


// =========================================================
// API HEALTH CHECK
// =========================================================

async function checkAPI() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/health`
        );

        if (!response.ok) {
            throw new Error("API unavailable");
        }

        systemStatus.textContent = "API Connected";

        statusIndicator.classList.add("online");

    } catch (error) {

        systemStatus.textContent = "API Offline";

        statusIndicator.classList.add("offline");

        console.error(
            "API health check failed:",
            error
        );
    }
}


// =========================================================
// LOAD SERVICES
// =========================================================

async function loadServices() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/services`
        );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }

        const data = await response.json();

        console.log(
            "Services API:",
            data
        );

        renderServices(data);

        populateServiceFilter(data);

    } catch (error) {

        console.error(
            "Failed to load services:",
            error
        );

        servicesTable.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="empty"
                >
                    Unable to load service SLA data.
                </td>
            </tr>
        `;
    }
}


// =========================================================
// RENDER SERVICE SLA TABLE
// =========================================================

function renderServices(data) {

    /*
        The API may return either:

        [
            {...},
            {...}
        ]

        or:

        {
            "services": [...]
        }
    */

    let services = data;

    if (!Array.isArray(services)) {

        services =
            data.services ||
            data.data ||
            [];
    }


    if (services.length === 0) {

        servicesTable.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="empty"
                >
                    No SLA service data available.
                </td>
            </tr>
        `;

        return;
    }


    servicesTable.innerHTML = "";


    services.forEach(service => {

        const availability =
            Number(
                service.availability_percent ??
                service.availability ??
                0
            );


        const status =
            service.sla_status ??
            (
                availability >= 99.9
                    ? "MET"
                    : "BREACHED"
            );


        const row =
            document.createElement("tr");


        row.innerHTML = `

            <td>
                <strong>
                    ${service.service_id ?? "-"}
                </strong>
            </td>

            <td>
                ${formatNumber(
                    service.expected_slots
                )}
            </td>

            <td>
                ${formatNumber(
                    service.available_slots
                )}
            </td>

            <td>
                ${formatNumber(
                    service.failed_slots
                )}
            </td>

            <td>
                ${formatNumber(
                    service.missing_slots
                )}
            </td>

            <td>
                ${availability.toFixed(4)}%
            </td>

            <td>

                <span
                    class="${
                        status === "MET"
                            ? "sla-met"
                            : "sla-breached"
                    }"
                >
                    ${status}
                </span>

            </td>
        `;


        servicesTable.appendChild(row);

    });

}


// =========================================================
// POPULATE SERVICE FILTER
// =========================================================

function populateServiceFilter(data) {

    let services = data;

    if (!Array.isArray(services)) {

        services =
            data.services ||
            data.data ||
            [];
    }


    serviceFilter.innerHTML = `
        <option value="">
            All Services
        </option>
    `;


    services.forEach(service => {

        const id =
            service.service_id;

        if (!id) {
            return;
        }


        const option =
            document.createElement("option");

        option.value = id;

        option.textContent = id;

        serviceFilter.appendChild(option);

    });

}


// =========================================================
// LOAD SUMMARY
// =========================================================

async function loadSummary() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/summary`
        );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }

        const data =
            await response.json();

        console.log(
            "Summary API:",
            data
        );

        renderSummary(data);

    } catch (error) {

        console.error(
            "Failed to load summary:",
            error
        );

        overallAvailability.textContent =
            "--";

        overallStatus.textContent =
            "Unavailable";
    }
}


// =========================================================
// RENDER SUMMARY
// =========================================================

function renderSummary(data) {

    /*
        Supports slightly different
        API response structures.
    */

    const summary =
        data.summary ||
        data;


    const services =
        summary.total_services ??
        summary.services ??
        0;


    const availability =
        Number(
            summary.overall_availability ??
            summary.availability_percent ??
            summary.availability ??
            0
        );


    const target =
        Number(
            summary.sla_target_percent ??
            summary.sla_target ??
            99.9
        );


    const failed =
        summary.failed_slots ??
        summary.total_failed_slots ??
        0;


    const missing =
        summary.missing_slots ??
        summary.total_missing_slots ??
        0;


    const status =
        summary.sla_status ??
        (
            availability >= target
                ? "MET"
                : "BREACHED"
        );


    totalServices.textContent =
        formatNumber(services);


    overallAvailability.textContent =
        `${availability.toFixed(4)}%`;


    slaTarget.textContent =
        `${target.toFixed(2)}%`;


    overallStatus.textContent =
        status;


    failedSlots.textContent =
        formatNumber(failed);


    missingSlots.textContent =
        formatNumber(missing);

}


// =========================================================
// LOAD LOGS
// =========================================================

async function loadLogs() {

    try {

        logsTable.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="empty"
                >
                    Loading logs...
                </td>
            </tr>
        `;


        const params =
            new URLSearchParams();


        // -----------------------------------------------
        // START DATE
        // -----------------------------------------------

        if (startDate.value) {

            params.append(
                "start_date",
                startDate.value
            );

        }


        // -----------------------------------------------
        // END DATE
        // -----------------------------------------------

        if (endDate.value) {

            params.append(
                "end_date",
                endDate.value
            );

        }


        // -----------------------------------------------
        // SERVICE
        // -----------------------------------------------

        if (serviceFilter.value) {

            params.append(
                "service_id",
                serviceFilter.value
            );

        }


        // -----------------------------------------------
        // LIMIT
        // -----------------------------------------------

        params.append(
            "limit",
            logLimit.value
        );


        const url =
            `${API_BASE_URL}/api/logs?${params.toString()}`;


        console.log(
            "Logs API:",
            url
        );


        const response =
            await fetch(url);


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "Logs response:",
            data
        );


        renderLogs(data);


    } catch (error) {

        console.error(
            "Failed to load logs:",
            error
        );


        logsTable.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="empty"
                >
                    Unable to load logs.
                </td>
            </tr>
        `;


        logCount.textContent =
            "Unable to load logs";

    }

}


// =========================================================
// RENDER LOGS
// =========================================================

function renderLogs(data) {

    const logs =
        data.logs ||
        data.data ||
        [];


    logCount.textContent =
        `${logs.length.toLocaleString()} records`;


    if (logs.length === 0) {

        logsTable.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="empty"
                >
                    No logs found for the selected filters.
                </td>
            </tr>
        `;

        return;
    }


    logsTable.innerHTML = "";


    logs.forEach(log => {

        const row =
            document.createElement("tr");


        const statusCode =
            Number(log.status_code);


        const statusClass =
            statusCode >= 200 &&
            statusCode < 300
                ? "http-success"
                : "http-failure";


        let timestamp = "-";


        if (log.timestamp_utc) {

            timestamp =
                new Date(
                    log.timestamp_utc
                ).toLocaleString();

        }


        let latency = "-";


        if (
            log.latency_ms !== null &&
            log.latency_ms !== undefined
        ) {

            latency =
                `${Number(
                    log.latency_ms
                ).toFixed(2)} ms`;

        }


        row.innerHTML = `

            <td>
                <strong>
                    ${escapeHTML(
                        log.service_id ?? "-"
                    )}
                </strong>
            </td>

            <td>
                ${timestamp}
            </td>

            <td>
                ${escapeHTML(
                    log.agent ?? "-"
                )}
            </td>

            <td>
                ${escapeHTML(
                    log.region ?? "-"
                )}
            </td>

            <td
                class="${statusClass}"
            >
                ${escapeHTML(
                    String(
                        log.status_code ?? "-"
                    )
                )}
            </td>

            <td>
                ${latency}
            </td>

            <td>
                ${escapeHTML(
                    log.source_file ?? "-"
                )}
            </td>

        `;


        logsTable.appendChild(row);

    });

}


// =========================================================
// FILTER BUTTON
// =========================================================

applyFilters.addEventListener(
    "click",
    () => {

        if (
            startDate.value &&
            endDate.value &&
            startDate.value > endDate.value
        ) {

            alert(
                "Start date cannot be after end date."
            );

            return;
        }


        loadLogs();

    }
);


// =========================================================
// CLEAR FILTERS
// =========================================================

clearFilters.addEventListener(
    "click",
    () => {

        startDate.value = "";

        endDate.value = "";

        serviceFilter.value = "";

        logLimit.value = "100";

        loadLogs();

    }
);


// =========================================================
// UPLOAD
// =========================================================

uploadButton.addEventListener(
    "click",
    async () => {

        const file =
            csvFile.files[0];


        if (!file) {

            showUploadMessage(
                "Please select a CSV file first.",
                "error"
            );

            return;
        }


        if (
            !file.name
                .toLowerCase()
                .endsWith(".csv")
        ) {

            showUploadMessage(
                "Only CSV files are allowed.",
                "error"
            );

            return;
        }


        /*
            The upload endpoint will be connected
            once the serverless ingestion function
            is implemented.

            For now we clearly tell the user
            that upload processing is not active.
        */

        showUploadMessage(
            "CSV selected successfully. Upload processing will be connected to the serverless ingestion function next.",
            "success"
        );

    }
);


// =========================================================
// UPLOAD MESSAGE
// =========================================================

function showUploadMessage(
    message,
    type
) {

    uploadMessage.textContent =
        message;

    uploadMessage.className =
        `message ${type}`;

}


// =========================================================
// NUMBER FORMATTER
// =========================================================

function formatNumber(value) {

    if (
        value === null ||
        value === undefined ||
        Number.isNaN(Number(value))
    ) {

        return "0";

    }


    return Number(value)
        .toLocaleString();

}


// =========================================================
// HTML ESCAPE
// =========================================================

function escapeHTML(value) {

    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


// =========================================================
// INITIALIZE DASHBOARD
// =========================================================

async function initializeDashboard() {

    console.log(
        "Initializing SLA dashboard..."
    );


    await checkAPI();


    await loadSummary();


    await loadServices();


    await loadLogs();

}


// =========================================================
// START
// =========================================================

initializeDashboard();