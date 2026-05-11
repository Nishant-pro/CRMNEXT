document.addEventListener("DOMContentLoaded", function() {
    // Generic form submission handler
    function handleForm(formId, endpoint, logElementId) {
        const form = document.getElementById(formId);
        form.addEventListener("submit", function(e) {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());
            // Convert numeric fields
            if (data.parallel) data.parallel = parseInt(data.parallel);
            if (data.server_id) data.server_id = parseInt(data.server_id);

            fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(res => {
                document.getElementById(logElementId).textContent = "Job submitted: " + res.job_id;
                pollJobLog(res.db_job_id, logElementId); // optional polling
            });
        });
    }

    handleForm("dp-export-form", "/api/export/datapump", "dp-export-log");
    handleForm("dp-import-form", "/api/import/datapump", "dp-import-log");
    handleForm("classic-export-form", "/api/export/classic", "classic-export-log");
    handleForm("classic-import-form", "/api/import/classic", "classic-import-log");

    // Tablespace fetch
    document.getElementById("tablespace-form").addEventListener("submit", function(e){
        e.preventDefault();
        const formData = new FormData(this);
        const data = { server_id: parseInt(formData.get("server_id")) };
        fetch("/api/tablespace", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(rows => {
            const tbody = document.querySelector("#tablespace-table tbody");
            tbody.innerHTML = "";
            rows.forEach(row => {
                const tr = document.createElement("tr");
                tr.innerHTML = `<td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td>${row[3]}</td><td>${row[4]}</td>`;
                tbody.appendChild(tr);
            });
            document.getElementById("tablespace-table").classList.remove("d-none");
        });
    });

    window.loadJobHistory = function() {
        fetch("/api/job/history")
        .then(r => r.json())
        .then(jobs => {
            const tbody = document.getElementById("history-body");
            tbody.innerHTML = "";
            jobs.forEach(j => {
                const tr = document.createElement("tr");
                tr.innerHTML = `<td>${j.id}</td><td>${j.type}</td><td>${j.status}</td><td>${j.created_at}</td>`;
                tbody.appendChild(tr);
            });
        });
    };

    function pollJobLog(dbJobId, logElementId) {
        // Simple polling for demonstration
        const interval = setInterval(() => {
            fetch(`/api/job/${dbJobId}/log`)
            .then(r => r.json())
            .then(data => {
                if (data.log) {
                    document.getElementById(logElementId).textContent = data.log;
                }
            });
        }, 5000);
    }
});
