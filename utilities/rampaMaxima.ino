#include <Arduino.h>

// ================= CONFIGURAÇÕES DO MOTOR =================
const int EN_PIN = 18;
const int R_PWM_PIN = 19;
const int L_PWM_PIN = 21;
const int pwmResolution = 12;
const int chR = 0;
const int chL = 1;

int rampa = 0;

uint16_t freq = 967;

// ================= FUNÇÕES DO MOTOR =================
inline void TurnRight(uint16_t speed) {
  ledcWrite(chL, 0);
  ledcWrite(chR, speed);
}

inline void Stop() {
  ledcWrite(chR, 0);
  ledcWrite(chL, 0);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==============================");
  Serial.println("INICIANDO SISTEMA MOTOR ESP32");
  Serial.println("==============================");

  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH);

  Serial.println("[SETUP] EN_PIN ativado");

  ledcSetup(chR, freq, pwmResolution);
  ledcAttachPin(R_PWM_PIN, chR);

  ledcSetup(chL, freq, pwmResolution);
  ledcAttachPin(L_PWM_PIN, chL);

  Serial.println("[SETUP] PWM configurado");
  Serial.println("[SETUP] Aguardando estabilização...");

  Stop();
  delay(2000);

  Serial.println("[SETUP] Sistema pronto!");
}

void loop() {

  Serial.print("[LOOP] Tempo(ms): ");
  Serial.print(millis());

  if (rampa == 0) {
    Serial.println(" | FASE: RAMPA DE ACELERACAO");

    for (int x = 0; x <= 4095; x += 10) {
      TurnRight((uint16_t)x);

      Serial.print("[RAMPA] PWM = ");
      Serial.println(x);

      delay(2);
    }

    rampa = 1;

    Serial.println("[RAMPA] Finalizada. Motor em saturacao.");
  }
  else {
    TurnRight(4095);

    Serial.println("[ESTADO] PWM MAXIMO (4095) ATIVO");
  }
}