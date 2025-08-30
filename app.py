from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import cv2
import time
import requests
import threading
import base64
import json
from ultralytics import YOLO
from datetime import datetime
import os

# Initialize Flask application and WebSocket support
app = Flask(__name__)
app.config["SECRET_KEY"] = "fire_detection_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")

# System Configuration Parameters
ESP_IP = "192.168.2.131"  # Default ESP32 IP address (configurable via web interface)
SMOKE_THRESHOLD = 2600  # Emperically determined; Demo value for prototype
TEMP_THRESHOLD = 20  # Emperically determined; Demo value for prototype
FIRE_CHECK_DURATION = 20  # Duration (seconds); Demo value for prototype
TEMP_CHECK_INTERVAL = 1  # Interval (seconds) between temperature checks
TEMP_CHECK_ATTEMPTS = 20  # Number of temperature checks for confirmation

# Global system state variables
monitoring_active = False
current_status = {
    "smoke_level": 0,  # Current smoke sensor reading
    "temperature": 0,  # Current temperature reading
    "fire_detected": False,  # Fire detection status
    "alarm_active": False,  # Alarm activation status
    "last_update": None,  # Timestamp of last update
    "camera_status": "offline",  # Camera availability status
    "esp32_status": "offline",  # ESP32 connectivity status
    "monitoring_stage": "idle",  # Current monitoring stage
    "stage_description": "System is idle",  # Human-readable stage description
}

# Load pre-trained YOLO model for fire detection
try:
    model = YOLO("YOLOv11n_custom_fire.pt")
    print("✅ YOLO fire detection model loaded successfully!")
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    model = None


class FireDetectionSystem:
    """
    Core fire detection system implementing multi-modal detection pipeline:
    1. Smoke sensor monitoring (primary trigger)
    2. AI-powered visual fire detection (verification)
    3. Temperature monitoring (fallback safety measure)
    """

    def __init__(self):
        """Initialize the fire detection system components."""
        self.cap = None  # OpenCV camera capture object
        self.monitoring = False  # System monitoring state
        self.current_stage = "idle"  # Current detection pipeline stage

    def get_smoke_level(self):
        """
        Retrieve current smoke level from ESP32 smoke sensor.

        Returns:
            int: Smoke level in ppm, or None if ESP32 is unreachable
        """
        try:
            response = requests.get(f"http://{ESP_IP}/smoke", timeout=2)
            if response.status_code == 200:
                current_status["esp32_status"] = "online"
                return response.json()
            current_status["esp32_status"] = "offline"
            return None
        except requests.exceptions.RequestException as e:
            current_status["esp32_status"] = "offline"
            return None

    def get_temperature(self):
        """
        Retrieve current temperature from ESP32 temperature sensor.

        Returns:
            float: Temperature in Celsius, or None if ESP32 is unreachable
        """
        try:
            response = requests.get(f"http://{ESP_IP}/temperature", timeout=2)
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            return None

    def trigger_alarm(self):
        try:
            response = requests.post(f"http://{ESP_IP}/trigger_alarm", timeout=2)
            if response.text == "Alarm activated":
                current_status["alarm_active"] = True
                socketio.emit("alarm_triggered", {"status": "active"})
                return True
        except requests.exceptions.RequestException:
            pass
        return False

    def stop_alarm(self):
        try:
            response = requests.post(f"http://{ESP_IP}/stop_alarm", timeout=2)
            if response.text == "Alarm stopped":
                current_status["alarm_active"] = False
                socketio.emit("alarm_stopped", {"status": "inactive"})
                return True
        except requests.exceptions.RequestException:
            pass
        return False

    def detect_fire_in_camera(self):
        """Camera fire detection for verification stage"""
        if model is None:
            return False

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            current_status["camera_status"] = "offline"
            return False

        current_status["camera_status"] = "online"
        fire_detected = False
        start_time = time.time()

        try:
            while (time.time() - start_time) < FIRE_CHECK_DURATION:
                ret, frame = cap.read()
                if not ret:
                    break

                # Detect fire in frame
                fire_found, processed_frame = self.detect_fire_frame(frame)

                # Encode frame to base64 and emit
                _, buffer = cv2.imencode(".jpg", processed_frame)
                frame_b64 = base64.b64encode(buffer).decode("utf-8")
                socketio.emit(
                    "video_frame", {"frame": frame_b64, "fire_detected": fire_found}
                )

                if fire_found:
                    fire_detected = True
                    # Save evidence image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    cv2.imwrite(f"fire_detected_{timestamp}.jpg", frame)
                    socketio.emit(
                        "log_message",
                        {
                            "message": f"Fire confirmed by camera! Evidence saved as fire_detected_{timestamp}.jpg",
                            "type": "error",
                        },
                    )
                    break

                time.sleep(0.1)  # ~10 FPS

        finally:
            cap.release()
            current_status["camera_status"] = "offline"

        return fire_detected

    def detect_fire_frame(self, frame):
        if model is None:
            return False, frame

        try:
            results = model.predict(frame, conf=0.5, verbose=False)
            fire_classes = [
                "Cooking Oil",
                "Electrical",
                "Gas",
                "Liquid",
                "Metal",
                "Solid",
            ]

            for result in results:
                if hasattr(result, "boxes") and result.boxes is not None:
                    for box in result.boxes:
                        if hasattr(box, "cls"):
                            class_id = int(box.cls[0])
                            if class_id < len(result.names):
                                class_name = result.names[class_id]
                                if class_name in fire_classes:
                                    # Draw bounding box
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    cv2.rectangle(
                                        frame, (x1, y1), (x2, y2), (0, 0, 255), 2
                                    )
                                    cv2.putText(
                                        frame,
                                        f"FIRE: {class_name}",
                                        (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX,
                                        0.5,
                                        (0, 0, 255),
                                        2,
                                    )
                                    return True, frame
            return False, frame
        except Exception as e:
            print(f"Error in fire detection: {e}")
            return False, frame

    def monitor_temperature_fallback(self):
        """Temperature monitoring as fallback mechanism"""
        socketio.emit(
            "log_message",
            {
                "message": "Camera verification failed. Starting temperature monitoring as fallback...",
                "type": "warning",
            },
        )

        for attempt in range(TEMP_CHECK_ATTEMPTS):
            if not monitoring_active:
                socketio.emit(
                    "log_message",
                    {
                        "message": "Temperature monitoring stopped by user",
                        "type": "warning",
                    },
                )
                break

            # Always log the attempt number first
            socketio.emit(
                "log_message",
                {
                    "message": f"Temperature check {attempt + 1}/{TEMP_CHECK_ATTEMPTS}: Requesting reading...",
                    "type": "info",
                },
            )

            temp = self.get_temperature()

            if temp is not None:
                current_status["temperature"] = temp
                current_status["last_update"] = datetime.now().strftime("%H:%M:%S")

                socketio.emit("status_update", current_status)
                socketio.emit(
                    "log_message",
                    {
                        "message": f"Temperature reading received: {temp}°C",
                        "type": "success",
                    },
                )

                if temp > TEMP_THRESHOLD:
                    socketio.emit(
                        "log_message",
                        {
                            "message": f"🚨 Temperature threshold exceeded! {temp}°C > {TEMP_THRESHOLD}°C",
                            "type": "error",
                        },
                    )
                    return True
            else:
                socketio.emit(
                    "log_message",
                    {
                        "message": f"Failed to get temperature reading (ESP32 connection issue)",
                        "type": "error",
                    },
                )

            # Wait before next check
            socketio.emit(
                "log_message",
                {
                    "message": f"Waiting {TEMP_CHECK_INTERVAL} seconds before next check...",
                    "type": "info",
                },
            )
            time.sleep(TEMP_CHECK_INTERVAL)

        socketio.emit(
            "log_message",
            {
                "message": "Temperature monitoring completed. No sustained temperature rise detected.",
                "type": "info",
            },
        )
        return False


fire_system = FireDetectionSystem()


def sequential_monitoring_pipeline():
    """
    Sequential Fire Detection Pipeline:
    1. Smoke Monitoring (continuous)
    2. Camera Verification (when smoke threshold exceeded)
    3. Temperature Fallback (if camera fails to detect fire)
    4. Back to Smoke Monitoring
    """
    global monitoring_active, current_status

    socketio.emit(
        "log_message",
        {
            "message": "Starting sequential fire detection pipeline...",
            "type": "success",
        },
    )

    while monitoring_active:
        try:
            # STAGE 1: SMOKE MONITORING
            current_status["monitoring_stage"] = "smoke_monitoring"
            current_status["stage_description"] = (
                "Monitoring smoke levels (camera and temperature sensors OFF)"
            )
            current_status["camera_status"] = "offline"

            socketio.emit("status_update", current_status)
            socketio.emit(
                "log_message",
                {
                    "message": "Stage 1: Smoke monitoring active. Camera and temperature sensors OFF.",
                    "type": "info",
                },
            )

            # Continuous smoke monitoring
            smoke_detection_active = True
            while smoke_detection_active and monitoring_active:
                smoke = fire_system.get_smoke_level()
                # smoke = 3000

                if smoke is not None:
                    current_status["smoke_level"] = smoke
                    current_status["last_update"] = datetime.now().strftime("%H:%M:%S")
                    socketio.emit("status_update", current_status)

                    # Check if smoke threshold is exceeded
                    if smoke > SMOKE_THRESHOLD:
                        socketio.emit(
                            "log_message",
                            {
                                "message": f"🚨 SMOKE THRESHOLD EXCEEDED! Level: {smoke} ppm (Threshold: {SMOKE_THRESHOLD} ppm)",
                                "type": "warning",
                            },
                        )
                        smoke_detection_active = False  # Move to next stage
                    else:
                        socketio.emit(
                            "log_message",
                            {
                                "message": f"Smoke level normal: {smoke} ppm",
                                "type": "info",
                            },
                        )

                time.sleep(5)  # Check smoke every 5 seconds

            if not monitoring_active:
                break

            # STAGE 2: CAMERA VERIFICATION
            current_status["monitoring_stage"] = "camera_verification"
            current_status["stage_description"] = (
                "Camera verifying fire detection (smoke sensor OFF)"
            )
            socketio.emit("status_update", current_status)

            socketio.emit(
                "log_message",
                {
                    "message": "Stage 2: Starting camera verification. Smoke sensor OFF.",
                    "type": "warning",
                },
            )

            fire_confirmed_by_camera = fire_system.detect_fire_in_camera()

            if fire_confirmed_by_camera:
                # FIRE CONFIRMED - TRIGGER ALARM
                current_status["fire_detected"] = True
                current_status["monitoring_stage"] = "fire_confirmed"
                current_status["stage_description"] = (
                    "FIRE CONFIRMED by camera! Alarm triggered."
                )

                socketio.emit("status_update", current_status)
                socketio.emit(
                    "log_message",
                    {
                        "message": "🔥 FIRE CONFIRMED BY CAMERA! Triggering alarm system!",
                        "type": "error",
                    },
                )

                fire_system.trigger_alarm()

                # Keep alarm active until manually stopped
                while current_status["alarm_active"] and monitoring_active:
                    time.sleep(1)

                # Reset after alarm is stopped
                current_status["fire_detected"] = False
                current_status["monitoring_stage"] = "idle"
                current_status["stage_description"] = (
                    "Alarm stopped. Returning to smoke monitoring."
                )
                socketio.emit("status_update", current_status)

            else:
                # STAGE 3: TEMPERATURE FALLBACK
                current_status["monitoring_stage"] = "temp_fallback"
                current_status["stage_description"] = (
                    "Camera verification failed. Using temperature fallback."
                )
                current_status["camera_status"] = "offline"
                socketio.emit("status_update", current_status)

                socketio.emit(
                    "log_message",
                    {
                        "message": "Stage 3: Camera failed to detect fire. Starting temperature fallback monitoring.",
                        "type": "warning",
                    },
                )

                fire_confirmed_by_temp = fire_system.monitor_temperature_fallback()

                if fire_confirmed_by_temp:
                    # FIRE CONFIRMED BY TEMPERATURE
                    current_status["fire_detected"] = True
                    current_status["monitoring_stage"] = "fire_confirmed"
                    current_status["stage_description"] = (
                        "FIRE CONFIRMED by temperature! Alarm triggered."
                    )

                    socketio.emit("status_update", current_status)
                    socketio.emit(
                        "log_message",
                        {
                            "message": "🔥 FIRE CONFIRMED BY TEMPERATURE FALLBACK! Triggering alarm system!",
                            "type": "error",
                        },
                    )

                    fire_system.trigger_alarm()

                    # Keep alarm active until manually stopped
                    while current_status["alarm_active"] and monitoring_active:
                        time.sleep(1)

                    # Reset after alarm is stopped
                    current_status["fire_detected"] = False
                    current_status["monitoring_stage"] = "idle"
                    current_status["stage_description"] = (
                        "Alarm stopped. Returning to smoke monitoring."
                    )
                    socketio.emit("status_update", current_status)

                else:
                    # NO FIRE DETECTED - RETURN TO SMOKE MONITORING
                    socketio.emit(
                        "log_message",
                        {
                            "message": "No fire confirmed by temperature fallback. Returning to smoke monitoring.",
                            "type": "info",
                        },
                    )

                    current_status["monitoring_stage"] = "idle"
                    current_status["stage_description"] = (
                        "False alarm cleared. Returning to smoke monitoring."
                    )
                    socketio.emit("status_update", current_status)

                    # Brief pause before returning to smoke monitoring
                    time.sleep(5)

        except Exception as e:
            socketio.emit(
                "log_message",
                {"message": f"Error in monitoring pipeline: {str(e)}", "type": "error"},
            )
            time.sleep(5)  # Wait before retrying

    # Cleanup when monitoring stops
    current_status["monitoring_stage"] = "idle"
    current_status["stage_description"] = "Monitoring stopped"
    current_status["camera_status"] = "offline"
    current_status["fire_detected"] = False
    socketio.emit("status_update", current_status)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start_monitoring", methods=["POST"])
def start_monitoring():
    global monitoring_active
    monitoring_active = True

    # Start the sequential monitoring pipeline
    monitoring_thread = threading.Thread(target=sequential_monitoring_pipeline)
    monitoring_thread.daemon = True
    monitoring_thread.start()

    return jsonify({"status": "started"})


@app.route("/api/stop_monitoring", methods=["POST"])
def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    fire_system.stop_alarm()
    current_status["alarm_active"] = False
    current_status["fire_detected"] = False
    current_status["monitoring_stage"] = "idle"
    current_status["stage_description"] = "System stopped by user"
    current_status["camera_status"] = "offline"
    return jsonify({"status": "stopped"})


@app.route("/api/stop_alarm", methods=["POST"])
def stop_alarm_api():
    success = fire_system.stop_alarm()
    return jsonify({"success": success})


@app.route("/api/status")
def get_status():
    return jsonify(current_status)


@app.route("/api/settings", methods=["GET", "POST"])
def settings():
    global ESP_IP, SMOKE_THRESHOLD, TEMP_THRESHOLD

    if request.method == "POST":
        data = request.json
        ESP_IP = data.get("esp_ip", ESP_IP)
        SMOKE_THRESHOLD = data.get("smoke_threshold", SMOKE_THRESHOLD)
        TEMP_THRESHOLD = data.get("temp_threshold", TEMP_THRESHOLD)
        return jsonify({"status": "updated"})

    return jsonify(
        {
            "esp_ip": ESP_IP,
            "smoke_threshold": SMOKE_THRESHOLD,
            "temp_threshold": TEMP_THRESHOLD,
        }
    )


@socketio.on("connect")
def handle_connect():
    emit("status_update", current_status)


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
