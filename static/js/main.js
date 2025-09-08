// Sports Betting Advisor JavaScript Functions

async function fetchData(file, tableId) {
    try {
        const response = await fetch("static/data/" + file);
        if (!response.ok) {
            throw new Error("Failed to load " + file);
        }
        const data = await response.json();
        displayTable(data, tableId);
    } catch (error) {
        document.getElementById(tableId).innerHTML = `<p class="error">Error loading data.</p>`;
        console.error(error);
    }
}

async function loadLastUpdated(datetimeId) {
    try {
        const response = await fetch("static/data/last_updated.txt");
        if (!response.ok) {
            throw new Error("Failed to load last updated time.");
        }
        const lastUpdated = await response.text();
        document.getElementById(datetimeId).innerHTML = `Data last updated on: ${lastUpdated}`;
    } catch (error) {
        document.getElementById(datetimeId).innerHTML = "Last updated time not available.";
        console.error(error);
    }
}

function displayTable(data, tableId) {
    if (!data.length) {
        document.getElementById(tableId).innerHTML = "<p>No data available</p>";
        return;
    }
    
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const tbody = document.createElement("tbody");

    // Table headers, excluding game_id
    const headers = Object.keys(data[0]).filter(key => key !== "game_id");
    const headerRow = document.createElement("tr");
    headers.forEach(header => {
        const th = document.createElement("th");
        th.textContent = header;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    // Check if this is a "Best Odds per Game" table (Results table)
    const isResultsTable = tableId.toLowerCase().includes('results');

    // Table body
    data.forEach(row => {
        const tr = document.createElement("tr");
        headers.forEach(header => {
            const td = document.createElement("td");
            let cellValue = row[header] ?? 'N/A';
            
            // Round probability values to 2 decimal places and add % sign
            if (header.toLowerCase().includes('prob') && cellValue !== 'N/A' && !isNaN(cellValue)) {
                // If it's already a percentage (> 1), just round it
                if (cellValue > 1) {
                    cellValue = cellValue.toFixed(2) + '%';
                } else {
                    // If it's a decimal (0-1), convert to percentage
                    cellValue = (cellValue * 100).toFixed(2) + '%';
                }
            }
            // Round difference values to 2 decimal places and add color coding ONLY for Results tables
            else if (header.toLowerCase().includes('difference') && cellValue !== 'N/A' && !isNaN(cellValue)) {
                const numericValue = parseFloat(cellValue);
                cellValue = numericValue.toFixed(2);
                
                // Add color styling for positive/negative differences ONLY in "Best Odds per Game" tables
                if (isResultsTable) {
                    if (numericValue > 0) {
                        td.style.color = '#28a745'; // Green for positive
                        td.style.fontWeight = 'bold';
                    } else if (numericValue < 0) {
                        td.style.color = '#dc3545'; // Red for negative
                        td.style.fontWeight = 'bold';
                    }
                }
            }
            
            td.textContent = cellValue;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    document.getElementById(tableId).innerHTML = "";
    document.getElementById(tableId).appendChild(table);
}

function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });

    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-nav button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });

    // Show selected tab content
    document.getElementById(tabName + 'Tab').classList.add('active');

    // Add active class to clicked button
    event.target.classList.add('active');

    // Load data for the selected sport
    loadSportData(tabName);
}

function loadSportData(sport) {
    const betterOddsContainer = sport + 'BetterOddsContainer';
    const resultsContainer = sport + 'ResultsContainer';
    const datetimeContainer = sport + 'Datetime';

    // Load sport-specific data
    fetchData(sport + "_better_odds.json", betterOddsContainer);
    fetchData(sport + "_results.json", resultsContainer);
    loadLastUpdated(datetimeContainer);
}

// Initialize page when DOM is loaded
window.onload = function () {
    // Show NHL tab by default
    document.getElementById('nhlTab').classList.add('active');
    document.querySelector('[onclick="showTab(\'nhl\')"]').classList.add('active');
    
    // Load NHL data by default
    loadSportData('nhl');
};