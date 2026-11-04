// Button toggles LED: press once = ON, press again = OFF
const int BTN = 2;   // button pin
const int LED = 8;   // LED pin (through 1k resistor)

bool ledOn = false;
bool lastBtn = HIGH;

void setup() {
  pinMode(BTN, INPUT_PULLUP);  // internal pull-up, no extra resistor for button
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);      // start with LED off
}

void loop() {
  bool btn = digitalRead(BTN);

  if (lastBtn == HIGH && btn == LOW) {  // button just pressed
    ledOn = !ledOn;
    digitalWrite(LED, ledOn);
    delay(50);                          // simple debounce
  }

  lastBtn = btn;
}
