void setup() {
  Serial.begin(250000);
}


void loop() {
  uint32_t t = micros();
  uint16_t sensor = analogRead(A0); // precisão total

  uint8_t header[2] = {0xAA, 0x55};//header de sincronização

  // Envio binário (rápido)
  Serial.write(header, 2);
  Serial.write((uint8_t*)&t, 4);
  Serial.write((uint8_t*)&sensor, 2);

  delayMicroseconds(300);
}