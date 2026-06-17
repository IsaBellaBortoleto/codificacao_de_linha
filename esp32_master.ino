/*
 * ESP32 MASTER - ponte Serial -> ESP-NOW
 *
 * O Python faz ASCII, XOR e HDB3 no pipeline.py.
 * Esta ESP apenas recebe o sinal HDB3 pronto pela Serial e envia via ESP-NOW.
 *
 * Serial PC -> ESP:
 *   {"type":"send","hdb3":[1,0,-1,0],"len":4}
 *
 * Serial ESP -> PC:
 *   {"status":"sent","delivered":1,"slaves":2,"len":4}
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <ArduinoJson.h>

uint8_t SLAVE_1_MAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x01};
uint8_t SLAVE_2_MAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x02};

#define MAX_SYMBOLS 240

typedef struct {
  int8_t hdb3[MAX_SYMBOLS];
  uint16_t len;
} esp_now_msg_t;

esp_now_msg_t outMsg;
int deliveredCount = 0;
const int totalSlaves = 2;

void onSent(const uint8_t *mac, esp_now_send_status_t status) {
  if (status == ESP_NOW_SEND_SUCCESS) {
    deliveredCount++;
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"error\":\"esp_now_init\"}");
    return;
  }

  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peerInfo = {};
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  memcpy(peerInfo.peer_addr, SLAVE_1_MAC, 6);
  esp_now_add_peer(&peerInfo);

  memcpy(peerInfo.peer_addr, SLAVE_2_MAC, 6);
  esp_now_add_peer(&peerInfo);

  Serial.println("{\"status\":\"master_ready\"}");
}

void loop() {
  if (!Serial.available()) return;

  String linha = Serial.readStringUntil('\n');
  linha.trim();
  if (linha.length() == 0) return;

  StaticJsonDocument<4096> doc;
  DeserializationError err = deserializeJson(doc, linha);
  if (err) {
    Serial.println("{\"error\":\"json_parse\"}");
    return;
  }

  const char *type = doc["type"] | "";
  if (strcmp(type, "send") != 0) {
    Serial.println("{\"error\":\"invalid_type\"}");
    return;
  }

  JsonArray hdb3 = doc["hdb3"].as<JsonArray>();
  uint16_t len = doc["len"] | hdb3.size();

  if (len == 0 || len > MAX_SYMBOLS || hdb3.size() < len) {
    Serial.println("{\"error\":\"invalid_hdb3\"}");
    return;
  }

  memset(&outMsg, 0, sizeof(outMsg));
  outMsg.len = len;

  for (uint16_t i = 0; i < len; i++) {
    outMsg.hdb3[i] = (int8_t) hdb3[i].as<int>();
  }

  deliveredCount = 0;
  esp_now_send(SLAVE_1_MAC, (uint8_t*) &outMsg, sizeof(outMsg));
  esp_now_send(SLAVE_2_MAC, (uint8_t*) &outMsg, sizeof(outMsg));

  unsigned long inicio = millis();
  while (millis() - inicio < 500) {
    delay(10);
  }

  StaticJsonDocument<256> resp;
  resp["status"] = "sent";
  resp["delivered"] = deliveredCount;
  resp["slaves"] = totalSlaves;
  resp["len"] = outMsg.len;

  String saida;
  serializeJson(resp, saida);
  Serial.println(saida);
}
