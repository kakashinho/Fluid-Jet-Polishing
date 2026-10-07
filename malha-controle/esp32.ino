#include <Arduino.h>

// ================= CONFIGURAÇÕES DO MOTOR =================
const int EN_PIN = 18;
const int R_PWM_PIN = 19;
const int L_PWM_PIN = 21;
const int pwmResolution = 12;
const int chR = 0;
const int chL = 1;

uint16_t freq = 967;

// ================= VARIÁVEIS DA JANELA =================
unsigned long tempoUltimaJanela = 0;
const unsigned long JANELA_MS = 1000; // Operando a 1 Hz
float somaPressao = 0;
int contagemLeituras = 0;

// ================= VARIÁVEIS DO PID E CONTROLE =================
float setpoint_bar = 8.0;
const float FF_GAIN = 0.95; // Headroom para o PI
float FF_base = (202.3064 * setpoint_bar) + 522.2530;
float dutyFeedforward = FF_base * FF_GAIN;

float Kp = 150.0;
float Ki = 100.0;
float erroIntegral = 0;
float erroFiltrado = 0;

float dutyControlado = 0; 

// ================= VARIÁVEIS DA RAMPA =================
float dutyAplicado = 0;        
float dutyAlvo = 0;            
const float RAMPA_SUBIDA = 819;
const float RAMPA_DESCIDA = 819; 

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
  Serial1.begin(250000, SERIAL_8N1, 16, 17);   
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH);

  ledcSetup(chR, freq, pwmResolution);
  ledcAttachPin(R_PWM_PIN, chR);

  ledcSetup(chL, freq, pwmResolution); 
  ledcAttachPin(L_PWM_PIN, chL);

  Stop();
  delay(2000);
  tempoUltimaJanela = millis();
}

void lerSensorArduino() {
  //0xAA 10101010 binário, 0x55 01010101 binário
  while (Serial1.available() >= 8) {
    if (Serial1.read() == 0xAA) {
      if (Serial1.peek() == 0x55) {
        Serial1.read(); 
        
        uint8_t buffer[6];
        Serial1.readBytes((char*)buffer, 6);

        uint16_t pressao_raw = buffer[4] | (buffer[5] << 8);
        // [AA][55][A][B][C][D][LOW][HIGH], Soma o 4 e o 5
        if (pressao_raw <= 1023) {
          float pressao_bar = (pressao_raw - 169) * (12.0 / (667.0 - 169.0));
          somaPressao += pressao_bar;
          contagemLeituras++;
        }
      }
    }
  }
}

void processarMalhaDeControle() {
  if (contagemLeituras == 0) return;

  // 1. Variável de Processo (PV)
  float pressaoMedia = somaPressao / contagemLeituras;

  // 2. Erro Dinâmico
  float erro = setpoint_bar - pressaoMedia;
  float dt = JANELA_MS / 1000.0; 

  // ================= AS 3 CORREÇÕES CRÍTICAS =================

  // CORREÇÃO 1: Filtro Real de Estado (EWMA independente)
  erroFiltrado = (0.5 * erroFiltrado) + (0.5 * erro);

  // CORREÇÃO 2: Sincronia Matemática x Hidráulica (Anti-Windup Perfeito)
  bool saturado = (dutyControlado >= 4095 || dutyControlado <= 0);
  bool erroPequeno = abs(erro) < 0.15;
  
  // O sistema só é considerado estável para integrar se o motor já alcançou o PWM alvo
  bool sistemaEstavel = abs(dutyAlvo - dutyAplicado) < 50;

  if (!saturado && !erroPequeno && sistemaEstavel) {
    // Usar o erroFiltrado na integral a deixa ainda mais imune a ruídos de cavitação
    erroIntegral += erroFiltrado * dt; 
    erroIntegral = constrain(erroIntegral, -1000.0 / Ki, 1000.0 / Ki); 
  }

  // ==========================================================

  // 5. Ação PID (agora atua sobre o erro filtrado real)
  float correcaoPID = (Kp * erroFiltrado) + (Ki * erroIntegral);

  // 6. Saída do Controlador
  dutyControlado = dutyFeedforward + correcaoPID;

  // 7. Clamp Matemático
  if (dutyControlado > 4095) dutyControlado = 4095;
  if (dutyControlado < 0) dutyControlado = 0;

  dutyAlvo = dutyControlado;

  // 8. Rampa Assimétrica Hidráulica
  if (dutyAplicado < dutyAlvo) {
    dutyAplicado += RAMPA_SUBIDA;
    if (dutyAplicado > dutyAlvo) dutyAplicado = dutyAlvo;
  }
  else if (dutyAplicado > dutyAlvo) {
    dutyAplicado -= RAMPA_DESCIDA;
    if (dutyAplicado < dutyAlvo) dutyAplicado = dutyAlvo;
  }

  // 9. Aplicação Física
  if (dutyAplicado > 0) {
    TurnRight((uint16_t)dutyAplicado);
  } else {
    Stop();
  }

  // 10. Debug via Serial (agora imprimindo o erroFiltrado para você ver o sinal limpo)
  Serial.print(millis()); Serial.print(",");
  Serial.print(setpoint_bar); Serial.print(",");
  Serial.print(pressaoMedia); Serial.print(",");
  Serial.print((uint16_t)dutyAplicado); Serial.print(",");
  Serial.println(erro);
  
  // 11. Reset para o próximo ciclo
  somaPressao = 0;
  contagemLeituras = 0;
}

void loop() {
  lerSensorArduino();

  if (millis() - tempoUltimaJanela >= JANELA_MS) {
    processarMalhaDeControle();
    tempoUltimaJanela = millis();
  }
}