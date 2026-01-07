#include <WiFi.h>
#include <PubSubClient.h>

// PWM output pin (Nano ESP32)
const int ecgOutputPin = 9;

// WiFi credentials
const char* ssid = "DIGIFIBRA-7416";
const char* password = "MTNBQRRHNM";

// MQTT broker (PC Wi-Fi IP)
const char* mqtt_server = "192.168.1.129";
const int   mqtt_port   = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

// ECG waveform (8-bit)
int ecgWaveform[] = {
  100,105,110,120,135,150,160,175,190,200,210,220,230,240,250,255,
  245,230,200,170,140,100,80,70,65,60,65,70,80,90,100,110,
  120,130,140,150,160,170,180,190,200,210,220,230,240,250,255,
  250,240,230,220,210,200,190,180,170,160,150,140,130,120,110,100
};

int numPoints = sizeof(ecgWaveform) / sizeof(ecgWaveform[0]);
int currentPoint = 0;
long bpm = 60;
long delayBetweenPoints = (60L * 1000000L) / (bpm * numPoints);

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Reconnecting to MQTT...");
    if (client.connect("esp32_ecg")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, mqtt_port);

  Serial.print("Connecting to MQTT");
  if (client.connect("esp32_ecg")) {
    Serial.println(" -> connected");
  } else {
    Serial.print(" -> failed, rc=");
    Serial.println(client.state());
  }

  pinMode(ecgOutputPin, OUTPUT);
}

void loop() {
  // Output ECG sample
  analogWrite(ecgOutputPin, ecgWaveform[currentPoint]);

  // Build MQTT payload
  char payload[128];
  snprintf(payload, sizeof(payload),
           "ecg,sampling_rate=2000,source=esp32 v=%d,bpm=%ld",
           ecgWaveform[currentPoint], bpm);

  // Publish every 20 samples
  static int publishDivider = 0;
  if (++publishDivider >= 20) {
    if (client.connected()) {
      client.publish("ems/t1/g3", payload);
      Serial.print("Published: ");
      Serial.println(payload);
    } else {
      Serial.println("MQTT disconnected");
       reconnectMQTT();
    }
    publishDivider = 0;
  }

  client.loop();

  currentPoint++;
  if (currentPoint >= numPoints) {
    currentPoint = 0;
  }

  delayMicroseconds(delayBetweenPoints);
}


