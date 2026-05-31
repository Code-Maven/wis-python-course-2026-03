/**
 * AETHERIS // Main Client controller logic
 */

// Global App States
let appData = null;
let filteredCandidates = [];
let currentPlotFilter = 'all'; // 'all' or 'stable'

// Table Pagination and Sorting states
let currentPage = 1;
const pageSize = 10;
let sortColumn = 3; // Formation Energy by default
let sortAscending = true;

// Initialize components when DOM loads
document.addEventListener("DOMContentLoaded", () => {
    // 1. Sync energy above hull slider and text badge
    const hullSlider = document.getElementById("hull-input");
    const hullValDisplay = document.getElementById("hull-value-display");
    
    if (hullSlider && hullValDisplay) {
        hullSlider.addEventListener("input", (e) => {
            hullValDisplay.textContent = `${parseFloat(e.target.value).toFixed(2)} eV`;
        });
    }
    
    // 2. Setup Search Form Submission
    const searchForm = document.getElementById("search-form");
    if (searchForm) {
        searchForm.addEventListener("submit", (e) => {
            e.preventDefault();
            performScreeningQuery();
        });
    }
    
    // Adjust layout resize listener for plotly charts
    window.addEventListener("resize", () => {
        const plotDiv = document.getElementById("plotly-scatter-chart");
        if (plotDiv && plotDiv.style.display !== 'none' && appData) {
            Plotly.Plots.resize(plotDiv);
        }
    });
});

/**
 * Pre-populate search input via presets chips
 */
function setPreset(val) {
    const input = document.getElementById("elements-input");
    if (input) {
        input.value = val;
        input.focus();
    }
}

/**
 * Switch dashboard state displays (SPA Router)
 */
function switchView(viewId, message = "") {
    const views = ["welcome-view", "loading-view", "error-view", "results-view"];
    views.forEach(v => {
        document.getElementById(v).classList.remove("active");
    });
    
    const activeView = document.getElementById(viewId);
    activeView.classList.add("active");
    
    if (viewId === "loading-view" && message) {
        document.getElementById("loading-message").innerText = message;
    }
}

/**
 * Reset to home welcome view
 */
function resetToWelcome() {
    switchView("welcome-view");
}

/**
 * AJAX Core - Post queries and process results
 */
function performScreeningQuery() {
    const elements = document.getElementById("elements-input").value;
    const minBg = parseFloat(document.getElementById("min-bg-input").value) || 0.0;
    const maxBg = parseFloat(document.getElementById("max-bg-input").value) || 10.0;
    const maxHull = parseFloat(document.getElementById("hull-input").value);
    const stableOnly = document.getElementById("stable-only-input").checked;
    
    // Validate inputs
    if (minBg > maxBg) {
        alert("Minimum Band Gap cannot exceed Maximum Band Gap.");
        return;
    }
    
    // Trigger loader state
    switchView("loading-view", `Connecting to Materials Project API to search for elements: ${elements}...`);
    
    // Post to Flask API
    fetch("/api/analyze", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            elements: elements,
            min_bg: minBg,
            max_bg: maxBg,
            max_hull: maxHull,
            stable_only: stableOnly
        })
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 444) {
                throw new Error(`No structures found matching those elements. Double check symbols spelling.`);
            }
            if (response.status === 400) {
                return response.json().then(data => { throw new Error(data.error); });
            }
            throw new Error(`Server returned code ${response.status}. Please make sure your .env API key is active.`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            appData = data;
            filteredCandidates = [...data.candidates];
            currentPage = 1;
            currentPlotFilter = 'all';
            
            // Set Toggle button default
            document.getElementById("btn-toggle-all").classList.add("active");
            document.getElementById("btn-toggle-stable").classList.remove("active");
            
            // Render results
            populateInsightCards(data.stats);
            renderPlotlyVisualization();
            renderCrystalSystemMeters(data.crystal_distribution);
            renderCandidatesTable();
            
            // Transition view
            switchView("results-view");
        } else {
            throw new Error(data.error || "Unknown analysis processing failure.");
        }
    })
    .catch(error => {
        console.error("Screening Query Error:", error);
        document.getElementById("error-message").innerText = error.message;
        switchView("error-view");
    });
}

/**
 * Display Insight Counter Cards
 */
function populateInsightCards(stats) {
    document.getElementById("stat-total-hits").innerText = stats.total_retrieved.toLocaleString();
    document.getElementById("stat-candidates").innerText = stats.candidates_found.toLocaleString();
    document.getElementById("candidate-count-pill").innerText = stats.candidates_found.toLocaleString();
    
    if (stats.candidates_found > 0) {
        document.getElementById("stat-best-fe").innerText = `${stats.min_formation_energy_candidates} eV`;
        document.getElementById("stat-avg-eg").innerText = `${stats.avg_bandgap_candidates} eV`;
    } else {
        document.getElementById("stat-best-fe").innerText = "N/A";
        document.getElementById("stat-avg-eg").innerText = "N/A";
    }
}

/**
 * Render Crystal System Meters
 */
function renderCrystalSystemMeters(distribution) {
    const container = document.getElementById("crystal-systems-distribution");
    container.innerHTML = "";
    
    if (!distribution || distribution.length === 0) {
        container.innerHTML = `<p class="input-hint">No distribution data available</p>`;
        return;
    }
    
    // Sort descending
    distribution.sort((a,b) => b.count - a.count);
    
    // Find max value to determine percentage
    const maxVal = Math.max(...distribution.map(d => d.count)) || 1;
    
    distribution.forEach(d => {
        const percent = (d.count / maxVal) * 100;
        
        const row = document.createElement("div");
        row.className = "system-row";
        row.innerHTML = `
            <div class="system-info">
                <span class="system-name">${d.system}</span>
                <span class="system-count">${d.count} items</span>
            </div>
            <div class="meter-track">
                <div class="meter-fill" style="width: 0%"></div>
            </div>
        `;
        container.appendChild(row);
        
        // Micro-animation delay triggers bar grow
        setTimeout(() => {
            row.querySelector(".meter-fill").style.width = `${percent}%`;
        }, 100);
    });
}

/**
 * Render Interactive Scatter Plot via Plotly.js
 */
function renderPlotlyVisualization() {
    const plotContainer = document.getElementById("plotly-scatter-chart");
    if (!appData || !appData.plot_points || appData.plot_points.length === 0) {
        plotContainer.innerHTML = "<div class='no-results-alert'>No scatter data available.</div>";
        return;
    }
    
    let points = appData.plot_points;
    
    // Filter scatter based on toggle selection
    if (currentPlotFilter === 'stable') {
        points = points.filter(p => p.is_candidate);
    }
    
    // Prepare trace vectors
    const stablePoints = points.filter(p => p.is_candidate);
    const unstablePoints = points.filter(p => !p.is_candidate);
    
    const traces = [];
    
    // Unstable (Background Points)
    if (unstablePoints.length > 0) {
        traces.push({
            x: unstablePoints.map(p => p.x),
            y: unstablePoints.map(p => p.y),
            text: unstablePoints.map(p => p.formula),
            customdata: unstablePoints.map(p => [p.id, p.color_val, p.crystal]),
            name: "Other Materials",
            mode: "markers",
            type: "scatter",
            marker: {
                size: 7,
                color: "rgba(255, 255, 255, 0.2)",
                line: {
                    color: "rgba(0, 0, 0, 0.3)",
                    width: 0.5
                }
            },
            hovertemplate: 
                "<b>%{text}</b> (Unstable/Screened Out)<br>" +
                "Material ID: %{customdata[0]}<br>" +
                "Band Gap: %{x:.3f} eV<br>" +
                "Formation Energy: %{y:.3f} eV/atom<br>" +
                "Energy Above Hull: %{customdata[1]:.4f} eV/atom<br>" +
                "Crystal System: %{customdata[2]}<br>" +
                "<extra></extra>"
        });
    }
    
    // Screened Candidates
    if (stablePoints.length > 0) {
        traces.push({
            x: stablePoints.map(p => p.x),
            y: stablePoints.map(p => p.y),
            text: stablePoints.map(p => p.formula),
            customdata: stablePoints.map(p => [p.id, p.color_val, p.crystal]),
            name: "Screened Candidates",
            mode: "markers",
            type: "scatter",
            marker: {
                size: 10,
                color: stablePoints.map(p => p.color_val),
                colorscale: [
                    [0, '#10b981'],  // Highly stable: emerald
                    [0.5, '#3b82f6'], // Medium stable: blue
                    [1, '#8b5cf6']    // Outer stable: purple
                ],
                cmin: 0,
                cmax: Math.max(...stablePoints.map(p => p.color_val), 0.05),
                colorbar: {
                    title: {
                        text: "Energy Above Hull (eV)",
                        font: { color: "#9ca3af", size: 10 }
                    },
                    tickfont: { color: "#9ca3af" }
                },
                line: {
                    color: "#ffffff",
                    width: 1.5
                }
            },
            hovertemplate: 
                "<b>%{text}</b> <span style='color:#10b981;'>(Candidate)</span><br>" +
                "Material ID: %{customdata[0]}<br>" +
                "Band Gap: %{x:.3f} eV<br>" +
                "Formation Energy: %{y:.3f} eV/atom<br>" +
                "Energy Above Hull: %{customdata[1]:.4f} eV/atom<br>" +
                "Crystal System: %{customdata[2]}<br>" +
                "<extra></extra>"
        });
    }
    
    const layout = {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        margin: { t: 30, r: 10, l: 50, b: 50 },
        showlegend: currentPlotFilter !== 'stable',
        legend: {
            font: { color: "#9ca3af" },
            x: 0,
            y: 1
        },
        xaxis: {
            title: {
                text: "Band Gap (eV)",
                font: { color: "#f3f4f6", family: "Outfit", size: 13 }
            },
            gridcolor: "rgba(255, 255, 255, 0.04)",
            linecolor: "rgba(255, 255, 255, 0.08)",
            tickfont: { color: "#9ca3af", family: "JetBrains Mono" },
            zeroline: false
        },
        yaxis: {
            title: {
                text: "Formation Energy (eV/atom)",
                font: { color: "#f3f4f6", family: "Outfit", size: 13 }
            },
            gridcolor: "rgba(255, 255, 255, 0.04)",
            linecolor: "rgba(255, 255, 255, 0.08)",
            tickfont: { color: "#9ca3af", family: "JetBrains Mono" },
            zeroline: false
        },
        hovermode: "closest",
        dragmode: "pan"
    };
    
    const config = {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'toggleSpikelines']
    };
    
    Plotly.newPlot(plotContainer, traces, layout, config);
}

/**
 * Filter Visualizer plot data between All & Stable candidates
 */
function filterPlotData(stableOnly) {
    currentPlotFilter = stableOnly ? 'stable' : 'all';
    
    // Sync buttons active styling
    const btnAll = document.getElementById("btn-toggle-all");
    const btnStable = document.getElementById("btn-toggle-stable");
    
    if (stableOnly) {
        btnAll.classList.remove("active");
        btnStable.classList.add("active");
    } else {
        btnAll.classList.add("active");
        btnStable.classList.remove("active");
    }
    
    renderPlotlyVisualization();
}

/**
 * Render Candidates Explorer List Table with Search, Sort, and Page elements
 */
function renderCandidatesTable() {
    const tBody = document.getElementById("table-body");
    tBody.innerHTML = "";
    
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, filteredCandidates.length);
    
    if (filteredCandidates.length === 0) {
        document.getElementById("no-table-results").classList.remove("hidden");
        document.getElementById("pagination-start").innerText = "0";
        document.getElementById("pagination-end").innerText = "0";
        document.getElementById("pagination-total").innerText = "0";
        renderPaginationControls();
        return;
    }
    
    document.getElementById("no-table-results").classList.add("hidden");
    
    // Sort array
    sortCandidatesData();
    
    const pageItems = filteredCandidates.slice(startIdx, endIdx);
    
    pageItems.forEach(item => {
        const hullVal = item.energy_above_hull;
        let badgeClass = "hull-stable";
        
        if (hullVal > 0.05) badgeClass = "hull-moderate";
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>
                <a href="https://materialsproject.org/materials/${item.id}" target="_blank" rel="noopener noreferrer" class="id-link">
                    ${item.id} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:8px;"></i>
                </a>
            </td>
            <td><span class="chem-formula">${formatFormula(item.formula)}</span></td>
            <td><span class="val-mono">${item.band_gap.toFixed(3)}</span></td>
            <td><span class="val-mono">${item.formation_energy.toFixed(3)}</span></td>
            <td><span class="hull-badge ${badgeClass}">${item.energy_above_hull.toFixed(4)}</span></td>
            <td><span class="c-system-badge">${item.crystal_system}</span></td>
        `;
        tBody.appendChild(tr);
    });
    
    // Update pagination descriptors
    document.getElementById("pagination-start").innerText = (startIdx + 1).toLocaleString();
    document.getElementById("pagination-end").innerText = endIdx.toLocaleString();
    document.getElementById("pagination-total").innerText = filteredCandidates.length.toLocaleString();
    
    renderPaginationControls();
}

/**
 * Format molecular formula nicely with subscript tags for numbers
 */
function formatFormula(formula) {
    if (!formula || formula === "N/A") return "N/A";
    // Replace numeric values with subscripts
    return formula.replace(/([A-Za-z])(\d+)/g, "$1<sub>$2</sub>");
}

/**
 * Sort Table Action
 */
function sortTable(colIndex) {
    if (sortColumn === colIndex) {
        sortAscending = !sortAscending;
    } else {
        sortColumn = colIndex;
        sortAscending = true;
    }
    
    // Update active arrow design in headers
    const headers = document.querySelectorAll("#candidates-table th");
    headers.forEach((th, idx) => {
        const icon = th.querySelector("i");
        if (idx === colIndex) {
            icon.className = sortAscending ? "fa-solid fa-sort-up" : "fa-solid fa-sort-down";
            icon.style.opacity = 1;
        } else {
            icon.className = "fa-solid fa-sort";
            icon.style.opacity = 0.5;
        }
    });
    
    currentPage = 1;
    renderCandidatesTable();
}

/**
 * Sort candidate vector values locally
 */
function sortCandidatesData() {
    filteredCandidates.sort((a, b) => {
        let valA, valB;
        
        switch (sortColumn) {
            case 0: // ID
                valA = a.id;
                valB = b.id;
                break;
            case 1: // Formula
                valA = a.formula;
                valB = b.formula;
                break;
            case 2: // Band Gap
                valA = a.band_gap;
                valB = b.band_gap;
                break;
            case 3: // Formation energy
                valA = a.formation_energy;
                valB = b.formation_energy;
                break;
            case 4: // Energy above hull
                valA = a.energy_above_hull;
                valB = b.energy_above_hull;
                break;
            case 5: // Crystal system
                valA = a.crystal_system;
                valB = b.crystal_system;
                break;
            default:
                valA = a.formation_energy;
                valB = b.formation_energy;
        }
        
        if (typeof valA === "string") {
            return sortAscending ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else {
            return sortAscending ? valA - valB : valB - valA;
        }
    });
}

/**
 * Render pagination footer indicator buttons
 */
function renderPaginationControls() {
    const totalPages = Math.ceil(filteredCandidates.length / pageSize) || 1;
    const container = document.getElementById("pagination-numbers");
    container.innerHTML = "";
    
    // Prev & Next disabled logic
    document.getElementById("btn-prev-page").disabled = (currentPage === 1);
    document.getElementById("btn-next-page").disabled = (currentPage === totalPages);
    
    // Max 5 page numbers displayed dynamically
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement("button");
        btn.className = `num-btn ${i === currentPage ? 'active' : ''}`;
        btn.innerText = i;
        btn.onclick = () => {
            currentPage = i;
            renderCandidatesTable();
        };
        container.appendChild(btn);
    }
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderCandidatesTable();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredCandidates.length / pageSize) || 1;
    if (currentPage < totalPages) {
        currentPage++;
        renderCandidatesTable();
    }
}

/**
 * Live search filter inside the table candidate structures list
 */
function searchTable() {
    const query = document.getElementById("table-search").value.toLowerCase().trim();
    
    if (!appData || !appData.candidates) return;
    
    if (query === "") {
        filteredCandidates = [...appData.candidates];
    } else {
        filteredCandidates = appData.candidates.filter(item => {
            return item.formula.toLowerCase().includes(query) || item.id.toLowerCase().includes(query);
        });
    }
    
    currentPage = 1;
    renderCandidatesTable();
}

/**
 * Generate CSV text and trigger client file downloads
 */
function downloadCSV() {
    if (!appData || filteredCandidates.length === 0) return;
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Material ID,Chemical Formula,Band Gap (eV),Formation Energy (eV/atom),Energy Above Hull (eV/atom),Crystal System\n";
    
    filteredCandidates.forEach(row => {
        csvContent += `${row.id},${row.formula},${row.band_gap},${row.formation_energy},${row.energy_above_hull},${row.crystal_system}\n`;
    });
    
    const encodedUri = encodeURI(csvContent);
    const downloadAnchor = document.createElement("a");
    
    // File names based on elements
    const elementsStr = appData.searched_elements.join("_");
    
    downloadAnchor.setAttribute("href", encodedUri);
    downloadAnchor.setAttribute("download", `aetheris_candidates_${elementsStr}.csv`);
    document.body.appendChild(downloadAnchor);
    
    downloadAnchor.click();
    document.body.removeChild(downloadAnchor);
}
