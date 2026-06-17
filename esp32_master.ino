/*
 * ESP32 MASTER (Host B - Receptor)
 * Trabalho de Codificacao de Linha - HDB3
 *
 * Responsabilidade: apenas repassar dados.
 *   ESP32 Slave -> ESP-NOW -> ESP32 Master -> Serial -> PC B
 *
 * Todo o processamento (HDB3 decode, XOR, binario) e feito no PC via Python.
 *
 * Protocolo Serial (Master -> PC):
 *   JSON com o payload recebido e o MAC do remetente:
 *   {"from":"AA:BB:CC:DD:EE:FF", "payload":"0100000000110001"}
 *
 * Nao e necessario cadastrar MACs dos Slaves -
 * o Master aceita mensagens de qualquer peer.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

#define MAX_PAYLOAD 250

// Callback de recepcao ESP-NOW
void onReceive(const esp_now_recv_info_t *info, const uint8_t *data, int dataLen) {
  if (dataLen == 0 || dataLen > MAX_PAYLOAD) return;

  // Copiar payload para buffer com terminador
  char buf[MAX_PAYLOAD + 1];
  memcpy(buf, data, dataLen);
  buf[dataLen] = '\0';

  // MAC do Slave remetente
  const uint8_t *mac = info->src_addr;
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

  // Enviar ao PC via Serial como JSON
  // Formato: {"from":"XX:XX:XX:XX:XX:XX","payload":"...dados..."}
  Serial.print("{\"from\":\"");
  Serial.print(macStr);
  Serial.print("\",\"payload\":\"");
  Serial.print(buf);
  Serial.println("\"}");
}

// Setup
void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"status\":\"error\",\"msg\":\"ESP-NOW init failed\"}");
    return;
  }

  esp_now_register_recv_cb(onReceive);

  Serial.println("{\"status\":\"master_ready\"}");
}

void loop() {
  delay(10);
}
