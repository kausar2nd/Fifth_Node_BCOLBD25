# EXIREN - Multi-Modal Fire Detection System

**_BCOLBD 2025 AI Competition Submission_**

EXIREN is an intelligent fire detection system that combines IoT sensors, AI-powered computer vision, and real-time web monitoring to provide accurate, fast, and reliable fire detection with minimal false alarms.

## 🎯 System Overview

EXIREN implements a three-stage detection pipeline:

1. **Primary Detection**: Continuous smoke monitoring via ESP32 sensors
2. **AI Verification**: YOLOv11-powered visual fire confirmation when smoke threshold is exceeded
3. **Safety Fallback**: Temperature-based emergency detection for system redundancy

## 🚀 Key Features

- 🔥 **AI-Powered Fire Detection**: Custom-trained YOLOv11n (nano) model for visual fire identification
- 💨 **IoT Smoke Monitoring**: Real-time smoke level monitoring via ESP32 sensors
- 🌡️ **Temperature Safety Net**: Multi-point temperature monitoring for redundancy
- 📹 **Live Video Stream**: Real-time camera feed with fire detection overlay
- 🚨 **Smart Alert System**: Configurable thresholds with automatic and manual alarm controls
- 📊 **Real-time Dashboard**: Live data visualization and system status monitoring
- ⚙️ **Web-based Control**: Responsive web interface accessible from any device
- 🔧 **Configurable Parameters**: Adjustable detection thresholds and system settings

## File Structure

```bash
├── app.py                    # Flask web application
├── templates/
│   └── index.html            # Main web interface
├── static/
│   ├── style.css             # Styling and animations
│   └── script.js             # Frontend JavaScript
├── YOLOv11n_custom_fire.pt   # Custom trained YOLO model
└── requirements.txt          # Python dependencies
```

## 📋 Requirements

### Hardware Requirements

- ESP32 microcontroller with WiFi capability
- MQ-2 smoke sensor
- LM35 temperature sensor
- USB camera/webcam
- Computer/server for main application

### Software Requirements

- Python 3.8 or higher
- Modern web browser
- WiFi network for ESP32 connectivity

## 🏃‍♂️ How to Run This Project

### Step 1: Clone the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/kausar2nd/Fifth_Node_BCOLBD25.git
cd Fifth_Node_BCOLBD25
```

### Step 2: Install Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Step 3: Hardware Setup (Optional)

If you have the hardware components for full AI + IoT functionality:

1. **ESP32 Configuration**:
   - Flash the provided `ESP32_Setup/ESP32_Setup.ino` to your ESP32
   - Connect MQ-2 smoke sensor to pin 35
   - Connect LM35 temperature sensor to pin 34
   - Update WiFi credentials in the Arduino code

2. **Camera Setup**:
   - Connect USB camera to your computer
   - Ensure camera is accessible as device index 0

### Step 4: Model Setup

Ensure the pre-trained YOLO model `YOLOv11n_custom_fire.pt` is present in the root directory.

### Step 5: Run the Application

Start the Flask web application:

```bash
python app.py
```

### Step 6: Access the Web Interface

- Open your web browser
- Navigate to `http://localhost:5000`
- The web interface will load with the fire detection system dashboard
- Configure ESP32 IP and detection thresholds if you have the hardware
- Start monitoring using the web interface

> **Note**: The system can run in demo mode without physical hardware for testing the web interface and AI model capabilities.

## 🚀 Usage

### Starting the System

1. **Power on ESP32** and ensure it connects to WiFi
2. **Run the main application**:

   ```bash
   python app.py
   ```

3. **Open web browser** and navigate to `http://localhost:5000`
4. **Configure settings** if needed (ESP32 IP, thresholds)
5. **Start monitoring** using the web interface

### Web Interface Guide

#### Control Panel

- **Start/Stop Monitoring**: Control system operation
- **Emergency Stop**: Immediate alarm deactivation
- **Settings**: Configure IP addresses and detection thresholds

#### Real-time Monitoring

- **Live Camera Feed**: Video stream with AI detection overlay
- **Sensor Dashboard**: Current smoke levels and temperature readings
- **System Status**: ESP32 connectivity and camera status
- **Detection Pipeline**: Visual representation of current monitoring stage

## Web Interface Components

### 1. Control Panel

- **Start/Stop Monitoring**: Control system operation
- **Stop Alarm**: Manual alarm override
- **Settings**: Configure system parameters

### 2. Live Camera Feed

- Real-time video stream from camera
- Fire detection overlay with bounding boxes
- Camera status indicator

### 3. Sensor Dashboard

- Current smoke level with threshold indicators
- Temperature readings
- ESP32 connection status

### 4. Alert System

- Visual and audio fire alerts
- Alarm status and controls
- Real-time alert notifications

### 5. Data Visualization

- Real-time charts for smoke and temperature
- Historical data trends
- Automatic data retention (last 20 points)

### 6. System Log

- Real-time system events
- Error tracking and debugging
- Color-coded message types

## System Requirements

- **Python 3.8+**
- **Camera**: USB camera or webcam (index 0)
- **ESP32**: With smoke and temperature sensors
- **Network**: ESP32 and computer on same network

## API Endpoints

The web interface exposes several REST API endpoints:

- `GET /`: Main web interface
- `POST /api/start_monitoring`: Start fire detection
- `POST /api/stop_monitoring`: Stop fire detection
- `POST /api/stop_alarm`: Stop alarm manually
- `GET /api/status`: Get current system status
- `GET/POST /api/settings`: Get/update system settings

## WebSocket Events

Real-time communication via Socket.IO:

- `status_update`: Sensor data updates
- `video_frame`: Camera feed frames
- `alarm_triggered`: Fire alarm activation
- `alarm_stopped`: Alarm deactivation

## Configuration

### ESP32 Endpoints

The system expects the following ESP32 endpoints:

- `GET /smoke`: Returns current smoke level
- `GET /temperature`: Returns current temperature
- `POST /trigger_alarm`: Activates alarm
- `POST /stop_alarm`: Deactivates alarm

### Thresholds

Ther are demonstration threshold. Thresholds should be determined empirically and can be adjusted via the web interface:

- **Smoke**: 2600 ppm
- **Temperature**: 20°C
- **Fire Check Duration**: 10 seconds
- **Temperature Check Interval**: 1 seconds

## Fire Detection Classes

The YOLO model detects the following fire types:

- Cooking Oil
- Electrical
- Gas
- Liquid
- Metal
- Solid

## Troubleshooting

### Common Issues

1. **Camera Not Working**:
   - Check camera connection
   - Verify camera index (change from 0 if needed)
   - Ensure no other applications are using the camera

2. **ESP32 Connection Failed**:
   - Verify ESP32 IP address in settings
   - Check network connectivity
   - Ensure ESP32 web server is running

3. **YOLO Model Error**:
   - Verify `YOLOv11n_custom_fire.pt` file exists
   - Check model file integrity
   - Ensure ultralytics package is installed

4. **Web Interface Not Loading**:
   - Check if Flask server is running
   - Verify port 5000 is available
   - Check browser console for errors

### Performance Tips

- Reduce video frame rate if CPU usage is high
- Adjust YOLO confidence threshold for better performance
- Monitor system resources during operation

## Development

### Adding Features

1. **New Sensors**: Update `FireDetectionSystem` class
2. **UI Components**: Modify HTML template and CSS
3. **Real-time Features**: Add Socket.IO events
4. **API Endpoints**: Extend Flask routes

## License

This project is part of research on "Reducing False Alarms in Fire Detection Systems".

## Support

For issues and questions, check the system log in the web interface or run the CLI version for detailed debugging information.


