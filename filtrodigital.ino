// EMS 2022: digital fitler implementation in ESP32

#define DOUT_PIN 21 
#define ADC_PIN 28
#define M 6 //filter order
float x[M+1] = {0.0};
static double b[M+1] = {
0.03898293407830291,
0.11697295021925129,
0.20469620812626674,
0.24367914220456957,
0.20469620812626674,
0.11697295021925129,
0.03898293407830291
};

void setup() {
  Serial.begin(115200);
  pinMode(ADC_PIN, INPUT);
  pinMode(DOUT_PIN, OUTPUT);
  analogWriteFreq(2000);      
  analogWriteRange(1023);     
}

void loop() {
  // 1. Acquire ADC sample (convert to volts)
  x[0] = analogRead(ADC_PIN) * 3.3 / 1023.0;  // ESP32 ADC is 12-bit (0–4095)

  // 2. Create FIR output signal
  float y0 = 0.0;
  for (int i = 0; i <= M; i++) {
    y0 += b[i] * x[i];
  }

  int pwmValue = (int)(constrain(y0, 0.0, 3.3) * 1023.0 / 3.3);
  analogWrite(DOUT_PIN, pwmValue);

  // 4. Print input/output for monitoring in python app
  //Serial.print(x[0]);
  //Serial.print(" ");
  Serial.println(y0);

  // 5. Save current input value and shift every old input by 1
  for (int i = M; i > 0; i--) {
    x[i] = x[i - 1];
  }

  delayMicroseconds(200);
}