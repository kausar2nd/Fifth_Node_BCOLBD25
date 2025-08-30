// Socket.IO connection
const socket = io();

// DOM elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const stopAlarmBtn = document.getElementById('stopAlarmBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeModal = document.getElementById('closeModal');
const settingsForm = document.getElementById('settingsForm');

const systemStatus = document.getElementById('systemStatus');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');

const videoFeed = document.getElementById('videoFeed');
const videoOverlay = document.getElementById('videoOverlay');
const cameraStatus = document.getElementById('cameraStatus');

const smokeLevel = document.getElementById('smokeLevel');
const temperature = document.getElementById('temperature');
const esp32Status = document.getElementById('esp32Status');

const alertIndicator = document.getElementById('alertIndicator');
const alertText = document.getElementById('alertText');
const alertDetails = document.getElementById('alertDetails');

const logContainer = document.getElementById('logContainer');

// Chart setup
let sensorChart;
const chartData = {
    labels: [],
    datasets: [
        {
            label: 'Smoke Level',
            data: [],
            borderColor: '#ff6b6b',
            backgroundColor: 'rgba(255, 107, 107, 0.1)',
            tension: 0.4
        },
        {
            label: 'Temperature (°C)',
            data: [],
            borderColor: '#00d4aa',
            backgroundColor: 'rgba(0, 212, 170, 0.1)',
            tension: 0.4
        }
    ]
};

// Initialize chart
function initChart() {
    const ctx = document.getElementById('sensorChart').getContext('2d');
    sensorChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

// Event listeners
startBtn.addEventListener('click', startMonitoring);
stopBtn.addEventListener('click', stopMonitoring);
stopAlarmBtn.addEventListener('click', stopAlarm);
settingsBtn.addEventListener('click', openSettings);
closeModal.addEventListener('click', closeSettings);
settingsForm.addEventListener('submit', saveSettings);

// Close modal when clicking outside
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        closeSettings();
    }
});

// Functions
async function startMonitoring() {
    try {
        const response = await fetch('/api/start_monitoring', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'started') {
            startBtn.disabled = true;
            stopBtn.disabled = false;
            updateSystemStatus('online', 'System Online - Monitoring Active');
            addLogEntry('System started monitoring', 'success');
        }
    } catch (error) {
        addLogEntry('Failed to start monitoring: ' + error.message, 'error');
    }
}

async function stopMonitoring() {
    try {
        const response = await fetch('/api/stop_monitoring', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'stopped') {
            startBtn.disabled = false;
            stopBtn.disabled = true;
            stopAlarmBtn.disabled = true;
            updateSystemStatus('offline', 'System Offline');
            addLogEntry('System stopped monitoring', 'warning');
            hideVideoFeed();
        }
    } catch (error) {
        addLogEntry('Failed to stop monitoring: ' + error.message, 'error');
    }
}

async function stopAlarm() {
    try {
        const response = await fetch('/api/stop_alarm', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            stopAlarmBtn.disabled = true;
            updateAlertStatus(false, 'Alarm stopped');
            addLogEntry('Alarm manually stopped', 'warning');
        }
    } catch (error) {
        addLogEntry('Failed to stop alarm: ' + error.message, 'error');
    }
}

function openSettings() {
    settingsModal.style.display = 'block';
    loadCurrentSettings();
}

function closeSettings() {
    settingsModal.style.display = 'none';
}

async function loadCurrentSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();

        document.getElementById('espIp').value = settings.esp_ip;
        document.getElementById('smokeThreshold').value = settings.smoke_threshold;
        document.getElementById('tempThreshold').value = settings.temp_threshold;
    } catch (error) {
        addLogEntry('Failed to load settings: ' + error.message, 'error');
    }
}

async function saveSettings(e) {
    e.preventDefault();

    const settings = {
        esp_ip: document.getElementById('espIp').value,
        smoke_threshold: parseInt(document.getElementById('smokeThreshold').value),
        temp_threshold: parseInt(document.getElementById('tempThreshold').value)
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (data.status === 'updated') {
            closeSettings();
            addLogEntry('Settings updated successfully', 'success');
        }
    } catch (error) {
        addLogEntry('Failed to save settings: ' + error.message, 'error');
    }
}

function updateSystemStatus(status, text) {
    statusIndicator.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

function updateSensorData(data) {
    // Update sensor values
    smokeLevel.textContent = data.smoke_level || '0';
    temperature.textContent = data.temperature || '0';

    // Update ESP32 status
    esp32Status.textContent = data.esp32_status || 'Offline';
    esp32Status.className = data.esp32_status === 'online' ? 'status-online' : 'status-offline';

    // Update camera status
    cameraStatus.textContent = data.camera_status || 'Offline';
    cameraStatus.className = data.camera_status === 'online' ? 'status-online' : 'status-offline';

    // Update monitoring pipeline status
    updatePipelineStatus(data.monitoring_stage, data.stage_description);

    // Check thresholds
    if (data.smoke_level > 2600) {
        smokeLevel.classList.add('threshold-exceeded');
    } else {
        smokeLevel.classList.remove('threshold-exceeded');
    }

    if (data.temperature > 60) {
        temperature.classList.add('threshold-exceeded');
    } else {
        temperature.classList.remove('threshold-exceeded');
    }

    // Update chart
    updateChart(data);
}

function updateChart(data) {
    const now = new Date().toLocaleTimeString();

    // Add new data point
    chartData.labels.push(now);
    chartData.datasets[0].data.push(data.smoke_level || 0);
    chartData.datasets[1].data.push(data.temperature || 0);

    // Keep only last 20 data points
    if (chartData.labels.length > 20) {
        chartData.labels.shift();
        chartData.datasets[0].data.shift();
        chartData.datasets[1].data.shift();
    }

    sensorChart.update('none');
}

function updatePipelineStatus(stage, description) {
    // Update current stage description
    const currentStageDescription = document.getElementById('currentStageDescription');
    if (currentStageDescription) {
        currentStageDescription.textContent = description || 'System idle';
    }

    // Reset all stages
    const stages = ['stageSmoke', 'stageCamera', 'stageTemp'];
    stages.forEach(stageId => {
        const stageElement = document.getElementById(stageId);
        if (stageElement) {
            stageElement.classList.remove('active');
        }
    });

    // Activate current stage
    let activeStageId = '';
    switch (stage) {
        case 'smoke_monitoring':
            activeStageId = 'stageSmoke';
            break;
        case 'camera_verification':
            activeStageId = 'stageCamera';
            break;
        case 'temp_fallback':
            activeStageId = 'stageTemp';
            break;
        case 'fire_confirmed':
            // Show all stages as active for fire confirmed
            stages.forEach(stageId => {
                const stageElement = document.getElementById(stageId);
                if (stageElement) {
                    stageElement.classList.add('active');
                }
            });
            return;
    }

    if (activeStageId) {
        const activeStage = document.getElementById(activeStageId);
        if (activeStage) {
            activeStage.classList.add('active');
        }
    }
}

function updateAlertStatus(fireDetected, message) {
    const alertCard = document.querySelector('.alert-card');

    if (fireDetected) {
        alertCard.classList.add('fire-alert');
        alertText.textContent = '🚨 FIRE DETECTED!';
        alertDetails.innerHTML = '<p><strong>IMMEDIATE ACTION REQUIRED!</strong></p><p>' + message + '</p>';
        stopAlarmBtn.disabled = false;
    } else {
        alertCard.classList.remove('fire-alert');
        alertText.textContent = 'No Alerts';
        alertDetails.innerHTML = '<p>System monitoring for fire hazards...</p>';
    }
}

function updateVideoFeed(frameData) {
    if (frameData && frameData.frame) {
        videoFeed.src = 'data:image/jpeg;base64,' + frameData.frame;
        videoOverlay.style.display = 'none';

        if (frameData.fire_detected) {
            videoFeed.style.border = '3px solid #ff6b6b';
        } else {
            videoFeed.style.border = 'none';
        }
    }
}

function hideVideoFeed() {
    videoFeed.src = '';
    videoOverlay.style.display = 'flex';
    videoFeed.style.border = 'none';
}

function addLogEntry(message, type = 'info') {
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';

    const time = new Date().toLocaleTimeString();
    const typeClass = type === 'error' ? 'log-error' : type === 'warning' ? 'log-warning' : type === 'success' ? 'log-success' : '';

    logEntry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-message ${typeClass}">${message}</span>
    `;

    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;

    // Keep only last 100 log entries
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// Socket.IO event handlers
socket.on('connect', () => {
    addLogEntry('Connected to server', 'success');
});

socket.on('disconnect', () => {
    addLogEntry('Disconnected from server', 'error');
    updateSystemStatus('offline', 'Connection Lost');
});

socket.on('status_update', (data) => {
    updateSensorData(data);

    if (data.fire_detected) {
        updateAlertStatus(true, 'Fire detected by sensors and camera!');
        addLogEntry('🚨 FIRE DETECTED! Alarm triggered!', 'error');
    }
});

socket.on('video_frame', (data) => {
    updateVideoFeed(data);

    if (data.fire_detected) {
        addLogEntry('Fire detected in camera feed', 'error');
    }
});

socket.on('alarm_triggered', (data) => {
    updateAlertStatus(true, 'Alarm system activated');
    stopAlarmBtn.disabled = false;
    addLogEntry('🚨 ALARM TRIGGERED!', 'error');
});

socket.on('alarm_stopped', (data) => {
    updateAlertStatus(false, 'Alarm system deactivated');
    stopAlarmBtn.disabled = true;
    addLogEntry('Alarm stopped', 'warning');
});

socket.on('log_message', (data) => {
    addLogEntry(data.message, data.type);
});

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    addLogEntry('Fire Detection System initialized', 'success');

    // Load initial status
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateSensorData(data);
        })
        .catch(error => {
            addLogEntry('Failed to load initial status: ' + error.message, 'error');
        });
});

// Auto-refresh status every 30 seconds
setInterval(() => {
    if (!startBtn.disabled) return; // Only refresh when monitoring is active

    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateSensorData(data);
        })
        .catch(error => {
            console.error('Status refresh failed:', error);
        });
}, 30000);
