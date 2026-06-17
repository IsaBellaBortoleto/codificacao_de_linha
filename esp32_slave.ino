/*
 * ESP32 SLAVE (Host A — Transmissor)
 * Trabalho de Codificação de Linha — HDB3
 *
 * Responsabilidade: apenas repassar dados.
 *   PC A → Serial → ESP32 Slave → ESP-NOW → ESP32 Master
 *
 * Todo o processamento (HDB3, XOR, binário) é feito no PC via Python.
 *
 * Protocolo Serial (PC → Slave):
 *   Bytes crus terminados em '\n'
 *   Exemplo: "0100000000110001\n"
 *
 * Protocolo Serial (Slave → PC):
 *   Confirmação JSON: {"status":"sent"} ou {"status":"failed"}
 *
 * IMPORTANTE: Atualize MASTER_MAC com o MAC real do seu ESP32 Master.
 *             O mesmo sketch é gravado nos dois Slaves.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

// ── MAC do Master (atualize!) ──────────────────────────────────────────────
uint8_t MASTER_MAC[] = {0xD4, 0xE9, 0xF4, 0xB2, 0x0F, 0xC4};

#define MAX_PAYLOAD 250  // limite de payload ESP-NOW: 250 bytes

// ── Callback de envio ──────────────────────────────────────────────────────
volatile bool sendDone    = false;
volatile bool sendSuccess = false;

void onSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  sendSuccess = (status == ESP_NOW_SEND_SUCCESS);
  sendDone    = true;
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"status\":\"error\",\"msg\":\"ESP-NOW init failed\"}");
    return;
  }
  esp_now_register_send_cb(onSent);

  // Registrar Master como peer
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, MASTER_MAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("{\"status\":\"error\",\"msg\":\"peer add failed\"}");
    return;
  }

  Serial.println("{\"status\":\"slave_ready\"}");
}

// ── Loop ───────────────────────────────────────────────────────────────────
void loop() {
  if (!Serial.available()) return;

  // Ler payload do PC até '\n'
  String payload = Serial.readStringUntil('\n');
  payload.trim();
  if (payload.length() == 0) return;

  // Truncar se passar do limite ESP-NOW
  if (payload.length() > MAX_PAYLOAD) {
    payload = payload.substring(0, MAX_PAYLOAD);
  }

  // Enviar via ESP-NOW (dados crus, sem processamento)
  sendDone    = false;
  sendSuccess = false;

  uint8_t buf[MAX_PAYLOAD];
  uint8_t len = payload.length();
  memcpy(buf, payload.c_str(), len);

  esp_now_send(MASTER_MAC, buf, len);

  // Aguardar callback (máx 500ms)
  unsigned long t = millis();
  while (!sendDone && millis() - t < 500) delay(5);

  // Confirmar ao PC
  if (sendSuccess) {
    Serial.println("{\"status\":\"sent\"}");
  } else {
    Serial.println("{\"status\":\"failed\"}");
  }
}
