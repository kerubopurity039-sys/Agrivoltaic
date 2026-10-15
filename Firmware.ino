
#include <DHT.h>
#include <ESP32Servo.h>

// ---------- PINS ----------
#define DHT_PIN       4
#define DHT_TYPE      DHT11
#define SOIL_PIN      34
#define SERVO_PIN     18
#define PUMP_PIN      26

// to verify your driver switches ON with HIGH.
#define PUMP_ACTIVE   HIGH
#define PUMP_INACTIVE LOW

DHT dht(DHT_PIN, DHT_TYPE);
Servo panelServo;

// ---------- CALIBRATION ----------
//  measured ADC readings.
const int DRY_RAW = 3000;
const int WET_RAW = 1400;

// Relative moisture thresholds.
const int DRY_THRESHOLD = 35;
const int WET_THRESHOLD = 50;

// Demonstration-only shading thresholds.
const float SHADE_ON_TEMP_C = 30.0;
const float SHADE_OFF_TEMP_C = 27.0;

const int SHADE_ANGLE = 30;
const int OPEN_ANGLE = 100;

// Pump protection
const unsigned long MAX_PUMP_MS = 10000UL;
const unsigned long PUMP_COOLDOWN_MS = 30000UL;
const unsigned long READ_INTERVAL_MS = 2500UL;

bool pumpOn = false;
bool shadeOn = false;
bool irrigationRequested = false;

unsigned long pumpStartedAt = 0;
unsigned long lastPumpStoppedAt = 0;
unsigned long lastReadAt = 0;

int moisturePercent(int raw) {
  if (DRY_RAW == WET_RAW) return 0;

  int value = map(raw, DRY_RAW, WET_RAW, 0, 100);
  return constrain(value, 0, 100);
}

void stopPump() {
  digitalWrite(PUMP_PIN, PUMP_INACTIVE);

  if (pumpOn) {
    pumpOn = false;
    lastPumpStoppedAt = millis();
    Serial.println("Pump OFF");
  }
}

void startPump() {
  if (pumpOn) return;

  digitalWrite(PUMP_PIN, PUMP_ACTIVE);
  pumpOn = true;
  pumpStartedAt = millis();

  Serial.println("Pump ON");
}

void updatePump(int moisture) {
  // Latch a watering request until the soil reaches
  // the higher recovery threshold.
  if (moisture <= DRY_THRESHOLD) {
    irrigationRequested = true;
  }

  if (moisture >= WET_THRESHOLD) {
    irrigationRequested = false;
  }

  if (pumpOn) {
    if (millis() - pumpStartedAt >= MAX_PUMP_MS) {
      stopPump();
      Serial.println("Maximum pump runtime reached.");
    }
    return;
  }

  if (irrigationRequested) {
    bool cooldownFinished =
      (lastPumpStoppedAt == 0) ||
      (millis() - lastPumpStoppedAt >= PUMP_COOLDOWN_MS);

    if (cooldownFinished) {
      startPump();
    }
  }
}

void updatePanel(float temperature) {
  if (temperature >= SHADE_ON_TEMP_C && !shadeOn) {
    shadeOn = true;
    panelServo.write(SHADE_ANGLE);
    Serial.println("Panel: SHADE position");
  }

  if (temperature <= SHADE_OFF_TEMP_C && shadeOn) {
    shadeOn = false;
    panelServo.write(OPEN_ANGLE);
    Serial.println("Panel: OPEN position");
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, PUMP_INACTIVE);

  analogReadResolution(12);
  dht.begin();

  panelServo.setPeriodHertz(50);
  panelServo.attach(SERVO_PIN, 500, 2400);
  panelServo.write(OPEN_ANGLE);

  Serial.println("Agrivoltaic potato prototype ready.");
  Serial.println("Calibrate moisture before enabling the pump.");
}

void loop() {
  if (millis() - lastReadAt < READ_INTERVAL_MS) {
    // Keep checking pump timeout even between readings.
    if (pumpOn &&
        millis() - pumpStartedAt >= MAX_PUMP_MS) {
      stopPump();
      Serial.println("Maximum pump runtime reached.");
    }
    return;
  }

  lastReadAt = millis();

  int raw = analogRead(SOIL_PIN);
  int moisture = moisturePercent(raw);

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  Serial.println("\n--- AGRIVOLTAIC READINGS ---");
  Serial.print("Soil raw ADC: ");
  Serial.println(raw);

  Serial.print("Relative soil moisture: ");
  Serial.print(moisture);
  Serial.println("%");

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("DHT11 error. Check wiring.");
    // Do not update panel or irrigation from bad readings.
    return;
  }

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" C");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println("%");

  updatePump(moisture);
  updatePanel(temperature);

  Serial.print("Pump: ");
  Serial.println(pumpOn ? "ON" : "OFF");

  Serial.print("Panel: ");
  Serial.println(shadeOn ? "SHADE" : "OPEN");
}
