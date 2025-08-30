#include <WiFi.h>
#include <WebServer.h>

// WiFi Configuration - Update with your network credentials
const char* ssid = "EXIREN";
const char* password = "say my name";

// Sensor Pin Definitions
const int tempPin = 34;   // LM35 temperature sensor (analog input)
const int smokePin = 35;  // MQ-2 smoke sensor (analog input)

// Create web server instance
WebServer server(80);

void setup() {
  Serial.begin(9600);
  analogReadResolution(12);  // Set ADC resolution to 12-bit (0-4095)
  
  Serial.println("EXIREN ESP32 Sensor Interface Starting...");

  // Connect to WiFi network
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi Connected!");
  Serial.println("IP Address: " + WiFi.localIP().toString());
  Serial.println("Access endpoints at: http://" + WiFi.localIP().toString());

  // Configure HTTP endpoints
  setupWebEndpoints();
  
  // Start the web server
  server.begin();
  Serial.println("HTTP server started successfully!");
}

void loop() {
  server.handleClient();  // Handle incoming HTTP requests
}

void setupWebEndpoints() {
  // Endpoint: GET /smoke
  // Returns current smoke sensor reading (0-4095)
  server.on("/smoke", HTTP_GET, [](){
    int smokeLevel = analogRead(smokePin);
    server.send(200, "application/json", String(smokeLevel));
    Serial.println("Smoke level requested: " + String(smokeLevel));
  });

  // Endpoint: GET /temperature  
  // Returns averaged temperature reading in Celsius
  server.on("/temperature", HTTP_GET, [](){
    long sum = 0;
    int validReadings = 0;
    
    // Take multiple readings for accuracy
    for(int i = 0; i < 10; i++){
      int tempRaw = analogRead(tempPin);
      if (tempRaw > 0) {
        sum += tempRaw;
        validReadings++;
      }
      delayMicroseconds(100);
    }
    
    // Convert to Celsius: (ADC_value * 3.3V / 4095) * 100
    float temperature = 0;
    if (validReadings > 0) {
      temperature = (sum / (float)validReadings * 3.3 / 4095.0) * 100.0;
    }
    
    server.send(200, "application/json", String(temperature));
    Serial.println("Temperature requested: " + String(temperature) + "°C");
  });

  // Endpoint: POST /trigger_alarm
  // Activates the alarm system
  server.on("/trigger_alarm", HTTP_POST, [](){
    server.send(200, "text/plain", "Alarm activated");
    Serial.println("ALARM ACTIVATED via web request");
  });

  // Endpoint: POST /stop_alarm
  // Deactivates the alarm system
  server.on("/stop_alarm", HTTP_POST, [](){
    server.send(200, "text/plain", "Alarm stopped");
    Serial.println("Alarm deactivated via web request");
  });
}
