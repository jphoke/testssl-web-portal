// API base URL
const API_URL = '/api';

// Current scan tracking
let currentScanId = null;
let statusCheckInterval = null;

// DOM elements
const scanForm = document.getElementById('scanForm');
const scanButton = document.getElementById('scanButton');
const scanStatus = document.getElementById('scanStatus');
const scanResults = document.getElementById('scanResults');
const progressBar = document.getElementById('progressBar');
const statusText = document.getElementById('statusText');
const resultsContent = document.getElementById('resultsContent');
const recentScans = document.getElementById('recentScans');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRecentScans();
});

// Form submission
scanForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const host = document.getElementById('host').value;
    const port = document.getElementById('port').value;
    
    // Disable form
    scanButton.disabled = true;
    scanButton.textContent = 'Starting scan...';
    
    try {
        const response = await fetch(`${API_URL}/scans`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ host, port: parseInt(port) }),
        });
        
        if (!response.ok) {
            throw new Error('Failed to start scan');
        }
        
        const data = await response.json();
        currentScanId = data.id;
        
        // Show status
        scanStatus.classList.remove('hidden');
        scanResults.classList.add('hidden');
        
        // Start polling for status
        checkScanStatus();
        statusCheckInterval = setInterval(checkScanStatus, 2000);
        
    } catch (error) {
        alert('Error starting scan: ' + error.message);
        scanButton.disabled = false;
        scanButton.textContent = 'Start Scan';
    }
});

// Check scan status
async function checkScanStatus() {
    if (!currentScanId) return;
    
    try {
        const response = await fetch(`${API_URL}/scans/${currentScanId}/status`);
        const data = await response.json();
        
        // Update progress
        const progress = data.progress || 0;
        progressBar.style.width = `${progress}%`;
        
        // Update status text
        switch (data.status) {
            case 'queued':
                statusText.textContent = 'Scan queued...';
                break;
            case 'running':
                statusText.textContent = `Scanning... ${progress}%`;
                break;
            case 'completed':
                statusText.textContent = 'Scan completed!';
                clearInterval(statusCheckInterval);
                loadScanResults();
                break;
            case 'error':
                statusText.textContent = 'Scan failed';
                clearInterval(statusCheckInterval);
                resetForm();
                break;
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Load scan results
async function loadScanResults() {
    if (!currentScanId) return;
    
    try {
        const response = await fetch(`${API_URL}/scans/${currentScanId}/results`);
        const data = await response.json();
        
        // Hide status, show results
        scanStatus.classList.add('hidden');
        scanResults.classList.remove('hidden');
        
        // Display results
        displayResults(data);
        
        // Reset form
        resetForm();
        
        // Refresh recent scans
        loadRecentScans();
        
    } catch (error) {
        console.error('Error loading results:', error);
        alert('Error loading scan results');
    }
}

// Display scan results
function displayResults(data) {
    let html = `
        <div class="results-header">
            <h3>${data.host}:${data.port}</h3>
            <div class="grade grade-${data.grade}">${data.grade || 'N/A'}</div>
        </div>
    `;
    
    // Protocols
    if (data.results.protocols && Object.keys(data.results.protocols).length > 0) {
        html += '<div class="results-section"><h3>🔐 Protocol Support</h3>';
        
        // Sort protocols by version
        const protocolOrder = ['SSLv2', 'SSLv3', 'TLS1', 'TLS1_1', 'TLS1_2', 'TLS1_3'];
        protocolOrder.forEach(protocolId => {
            const protocol = data.results.protocols[protocolId];
            if (protocol) {
                const supported = protocol.supported;
                const className = supported ? 'protocol-supported' : 'protocol-not-supported';
                const icon = supported ? '✅' : '❌';
                const status = supported ? 'Supported' : 'Not Supported';
                
                // Color code based on protocol security
                let extraClass = '';
                if (protocolId === 'SSLv2' || protocolId === 'SSLv3' || protocolId === 'TLS1' || protocolId === 'TLS1_1') {
                    extraClass = supported ? 'vulnerability' : '';
                } else if (protocolId === 'TLS1_3') {
                    extraClass = supported ? 'protocol-modern' : '';
                }
                
                html += `<div class="result-item ${className} ${extraClass}">
                    ${icon} <strong>${protocol.name}</strong>: ${status}
                    ${supported && (protocolId === 'SSLv2' || protocolId === 'SSLv3' || protocolId === 'TLS1' || protocolId === 'TLS1_1') ? '<span class="warning"> ⚠️ Insecure!</span>' : ''}
                </div>`;
            }
        });
        html += '</div>';
    }
    
    // Vulnerabilities
    if (data.results.vulnerabilities && Object.keys(data.results.vulnerabilities).length > 0) {
        html += '<div class="results-section"><h3>🛡️ Vulnerability Assessment</h3>';
        let hasVulnerabilities = false;
        
        for (const [vuln, info] of Object.entries(data.results.vulnerabilities)) {
            if (info.vulnerable) {
                hasVulnerabilities = true;
                html += `<div class="result-item vulnerability">
                    ⚠️ <strong>${vuln}</strong>: VULNERABLE
                    ${info.cve ? `<span class="cve">(${info.cve})</span>` : ''}
                    <div class="finding-detail">${info.finding}</div>
                </div>`;
            } else {
                html += `<div class="result-item safe">
                    ✅ <strong>${vuln}</strong>: Not vulnerable
                </div>`;
            }
        }
        
        if (!hasVulnerabilities) {
            html += '<div class="result-item safe">✅ No vulnerabilities detected!</div>';
        }
        html += '</div>';
    }
    
    // Certificate information
    if (data.results.certificate && Object.keys(data.results.certificate).length > 0) {
        html += '<div class="results-section"><h3>📜 Certificate Information</h3>';
        const cert = data.results.certificate;
        
        // Only display expiration status
        const expirationField = cert.cert_expirationStatus || cert.cert_validity || cert.cert_validityPeriod;
        
        if (expirationField) {
            let itemClass = 'result-item safe';  // Default to green
            let warningIcon = '✅ ';
            
            // Check for expiration conditions
            if (expirationField.includes('expired')) {
                itemClass = 'result-item vulnerability';  // Red
                warningIcon = '❌ ';
            } else if (expirationField.includes('expires <')) {
                if (expirationField.includes('< 30 days')) {
                    itemClass = 'result-item vulnerability';  // Red for < 30 days
                    warningIcon = '⚠️ ';
                } else if (expirationField.includes('< 60 days')) {
                    itemClass = 'result-item medium-strength';  // Yellow for < 60 days
                    warningIcon = '⚠️ ';
                }
            }
            
            html += `<div class="${itemClass}">
                ${warningIcon}<strong>Certificate Expiration:</strong> ${expirationField}
            </div>`;
        }
        
        html += '</div>';
    }
    
    // Cipher Suites
    if (data.results.ciphers && Object.keys(data.results.ciphers).length > 0) {
        html += '<div class="results-section"><h3>🔑 Cipher Suites</h3>';
        let cipherCount = 0;
        let weakCount = 0;
        let allCiphers = [];
        
        for (const [category, ciphers] of Object.entries(data.results.ciphers)) {
            if (Array.isArray(ciphers) && ciphers.length > 0) {
                cipherCount += ciphers.length;
                ciphers.forEach(cipher => {
                    if (cipher.strength === 'weak') weakCount++;
                    allCiphers.push({...cipher, category});
                });
            }
        }
        
        html += `<div class="result-item" style="cursor: pointer;" onclick="toggleCipherDetails()">
            <strong>Total Ciphers:</strong> ${cipherCount}
            ${weakCount > 0 ? `<span class="warning"> (${weakCount} weak ciphers detected)</span>` : ''}
            <span style="float: right; color: #3498db;">▼ Click to expand</span>
        </div>`;
        
        // Show cipher details if there are weak ones
        if (weakCount > 0) {
            html += '<div class="cipher-warning">⚠️ Weak ciphers should be disabled</div>';
        }
        
        // Hidden cipher details section
        html += '<div id="cipherDetails" class="hidden" style="margin-top: 15px;">';
        
        // Group ciphers by category
        const ciphersByCategory = {};
        allCiphers.forEach(cipher => {
            if (!ciphersByCategory[cipher.category]) {
                ciphersByCategory[cipher.category] = [];
            }
            ciphersByCategory[cipher.category].push(cipher);
        });
        
        // Display ciphers by category
        for (const [category, ciphers] of Object.entries(ciphersByCategory)) {
            html += `<div style="margin-bottom: 20px;">
                <h4 style="color: #2c3e50; margin-bottom: 10px;">${category}</h4>`;
            
            ciphers.forEach(cipher => {
                const strengthClass = cipher.strength === 'weak' ? 'vulnerability' : 
                                    cipher.strength === 'medium' ? 'medium-strength' : 'safe';
                const strengthIcon = cipher.strength === 'weak' ? '❌' : 
                                   cipher.strength === 'medium' ? '⚠️' : '✅';
                
                html += `<div class="result-item ${strengthClass}" style="font-size: 0.9em; padding: 8px 12px;">
                    ${strengthIcon} <code>${cipher.details || cipher.name}</code>
                </div>`;
            });
            
            html += '</div>';
        }
        
        html += '</div>';
        html += '</div>';
    }
    
    // Server Defaults
    if (data.results.server_defaults && Object.keys(data.results.server_defaults).length > 0) {
        html += '<div class="results-section"><h3>⚙️ Server Configuration</h3>';
        for (const [key, value] of Object.entries(data.results.server_defaults)) {
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            html += `<div class="result-item">
                <strong>${label}:</strong> ${value}
            </div>`;
        }
        html += '</div>';
    }
    
    // Security Headers
    if (data.results.headers && Object.keys(data.results.headers).length > 0) {
        html += '<div class="results-section"><h3>📋 Security Headers</h3>';
        for (const [header, info] of Object.entries(data.results.headers)) {
            const icon = info.severity === 'OK' ? '✅' : '⚠️';
            html += `<div class="result-item">
                ${icon} <strong>${header}:</strong> ${info.finding}
            </div>`;
        }
        html += '</div>';
    }
    
    resultsContent.innerHTML = html;
}

// Load recent scans
async function loadRecentScans() {
    try {
        const response = await fetch(`${API_URL}/scans?limit=10`);
        const scans = await response.json();
        
        if (scans.length === 0) {
            recentScans.innerHTML = '<p>No scans yet</p>';
            return;
        }
        
        let html = '';
        for (const scan of scans) {
            const date = new Date(scan.created_at).toLocaleString();
            html += `
                <div class="scan-item" onclick="viewScan('${scan.id}')" style="cursor: pointer;">
                    <div class="scan-info">
                        <h3>${scan.host}:${scan.port}</h3>
                        <p>${date} (UTC)</p>
                        <p style="font-size: 0.8em; color: #95a5a6;">ScanID: ${scan.id}</p>
                    </div>
                    <div>
                        ${scan.grade ? `<span class="grade grade-${scan.grade}">${scan.grade}</span>` : ''}
                        <span class="status status-${scan.status}">${scan.status}</span>
                    </div>
                </div>
            `;
        }
        
        recentScans.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading recent scans:', error);
        recentScans.innerHTML = '<p>Error loading scans</p>';
    }
}

// View a previous scan
async function viewScan(scanId) {
    currentScanId = scanId;
    try {
        const response = await fetch(`${API_URL}/scans/${scanId}/results`);
        const data = await response.json();
        
        if (data.status === 'completed') {
            scanStatus.classList.add('hidden');
            scanResults.classList.remove('hidden');
            displayResults(data);
        }
    } catch (error) {
        console.error('Error viewing scan:', error);
    }
}

// Reset form
function resetForm() {
    scanButton.disabled = false;
    scanButton.textContent = 'Start Scan';
    currentScanId = null;
    clearInterval(statusCheckInterval);
}

// Toggle cipher details visibility
function toggleCipherDetails() {
    const cipherDetails = document.getElementById('cipherDetails');
    const toggleText = event.target.querySelector('span[style*="float: right"]');
    
    if (cipherDetails.classList.contains('hidden')) {
        cipherDetails.classList.remove('hidden');
        if (toggleText) toggleText.textContent = '▲ Click to collapse';
    } else {
        cipherDetails.classList.add('hidden');
        if (toggleText) toggleText.textContent = '▼ Click to expand';
    }
}