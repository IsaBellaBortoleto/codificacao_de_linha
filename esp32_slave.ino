/*
 * ESP32 SLAVE - ponte ESP-NOW -> Serial
 *
 * O Python faz ASCII, XOR e HDB3 no pipeline.py.
 * Esta ESP apenas recebe o sinal HDB3 por ESP-NOW e envia para o PC.
 *
 * Serial ESP -> PC:
 *   {"type":"received","hdb3":[1,0,-1,0],"len":4}
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <ArduinoJson.h>

uint8_t MASTER_MAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x00};

#define MAX_SYMBOLS 240

typedef struct {
  int8_t hdb3[MAX_SYMBOLS];
  uint16_t len;
} esp_now_msg_t;

void onReceive(const uint8_t *mac, const uint8_t *data, int len) {
  if (len != sizeof(esp_now_msg_t)) return;

  esp_now_msg_t msg;
  memcpy(&msg, data, sizeof(msg));

  if (msg.len == 0 || msg.len > MAX_SYMBOLS) return;

  StaticJsonDocument<4096> doc;
  doc["type"] = "received";
  doc["len"] = msg.len;

  JsonArray hdb3 = doc.createNestedArray("hdb3");
  for (uint16_t i = 0; i < msg.len; i++) {
    hdb3.add(msg.hdb3[i]);
  }

  String saida;
  serializeJson(doc, saida);
  Serial.println(saida);
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"error\":\"esp_now_init\"}");
    return;
  }

  esp_now_register_recv_cb(onReceive);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, MASTER_MAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  Serial.println("{\"status\":\"slave_ready\"}");
}

void loop() {
  delay(10);
}
