// Ultrasonic Radar - HC-SR04 on an SG90 servo with a 3D-printed mount
#include <Servo.h>

const int TRIG_PIN  = 9;
const int ECHO_PIN  = 10;
const int SERVO_PIN = 6;

const int MIN_ANGLE = 15;
const int MAX_ANGLE = 165;
const int STEP      = 2;
const int SETTLE_MS = 30;     // time for the servo to reach each angle

const bool CENTER_MODE = false;   // true = hold at 90 degrees for mounting

Servo radarServo;

long readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);  // ~5 m timeout
  if (duration == 0) return -1;                               // no echo
  return duration / 58;                                       // microseconds -> cm
}

void scanAt(int angle) {
  radarServo.write(angle);
  delay(SETTLE_MS);
  long d = readDistanceCm();
  Serial.print(angle);
  Serial.print(',');
  Serial.println(d);                     // format: angle,distance
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.begin(9600);
  radarServo.attach(SERVO_PIN);
  radarServo.write(90);
  delay(1000);
}

void loop() {
  if (CENTER_MODE) return;
  for (int a = MIN_ANGLE; a <= MAX_ANGLE; a += STEP) scanAt(a);
  for (int a = MAX_ANGLE; a >= MIN_ANGLE; a -= STEP) scanAt(a);
}
