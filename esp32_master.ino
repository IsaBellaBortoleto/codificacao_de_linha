/*
 * ESP32 MASTER - HDB3 Line Coding
 * Trabalho de Codificação de Linha
 *
 * Fluxo:
 *   PC (Python) → Serial → ESP32 Master → HDB3 encode → ESP-NOW → ESP32 Slaves
 *
 * Protocolo Serial (PC → Master):
 *   Recebe JSON: {"bits":"0100000000110001", "key": 42}
 *
 * Protocolo Serial (Master → PC):
 *   Envia JSON com status de entrega: {"delivered": true, "slaves": 2}
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <ArduinoJson.h>

// ── Endereços MAC dos Slaves (atualize conforme seus dispositivos) ──────────
uint8_t SLAVE_1_MAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x01};
uint8_t SLAVE_2_MAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x02};

// ── Estrutura da mensagem ESP-NOW ──────────────────────────────────────────
#define MAX_BITS 512

typedef struct {
  int8_t  hdb3[MAX_BITS];   // sinal HDB3: -1, 0, +1
  uint16_t len;              // número de símbolos
  uint8_t  key;             // chave XOR de criptografia
  char     original[128];   // mensagem original (para depuração)
} esp_now_msg_t;

esp_now_msg_t outMsg;

// ── Estado AMI / HDB3 ──────────────────────────────────────────────────────
int  amiPolarity   = +1;   // próxima polaridade AMI (+1 ou -1)
int  nonZeroCount  = 0;    // pulsos não-zero desde última substituição HDB3

// ── Callback de envio ESP-NOW ──────────────────────────────────────────────
int deliveredCount = 0;
int totalSlaves    = 2;

void onSent(const uint8_t *mac, esp_now_send_status_t status) {
  if (status == ESP_NOW_SEND_SUCCESS) deliveredCount++;
}

// ── HDB3 Encoder ──────────────────────────────────────────────────────────
/*
 * HDB3: grupos de 4 zeros consecutivos são substituídos por:
 *   - 000V  se o número de pulsos não-zero desde a última substituição for ímpar
 *   - B00V  se for par
 *
 * V = mesma polaridade do último pulso não-zero (violação AMI)
 * B = polaridade oposta ao último pulso não-zero (segue regra AMI)
 */
void encodeHDB3(const uint8_t *bits, uint16_t len, int8_t *out, uint16_t &outLen) {
  // Primeiro, construir sequência AMI bruta
  int8_t raw[MAX_BITS];
  int polarity = +1;
  for (uint16_t i = 0; i < len; i++) {
    if (bits[i] == 0) {
      raw[i] = 0;
    } else {
      raw[i] = polarity;
      polarity = -polarity;
    }
  }

  // Aplicar substituição HDB3
  int8_t result[MAX_BITS];
  memcpy(result, raw, len * sizeof(int8_t));

  int lastNonZeroPol = +1;  // polaridade do último pulso não-zero
  int nonZeroSinceLast = 0; // pulsos não-zero desde última substituição

  uint16_t i = 0;
  while (i < len) {
    // Detectar grupo de 4 zeros
    if (i + 3 < len &&
        raw[i]==0 && raw[i+1]==0 && raw[i+2]==0 && raw[i+3]==0) {

      int8_t V = lastNonZeroPol;  // violação = mesma polaridade do último

      if (nonZeroSinceLast % 2 == 1) {
        // ímpar → 000V
        result[i]   =  0;
        result[i+1] =  0;
        result[i+2] =  0;
        result[i+3] =  V;
      } else {
        // par → B00V  (B tem polaridade OPOSTA a lastNonZeroPol → segue AMI)
        int8_t B = -lastNonZeroPol;
        result[i]   =  B;
        result[i+1] =  0;
        result[i+2] =  0;
        result[i+3] =  V;
        lastNonZeroPol = B;
        nonZeroSinceLast++;  // B conta como pulso não-zero
      }

      // V foi inserido; atualizar estado
      lastNonZeroPol = V;
      nonZeroSinceLast = 0;  // reset após substituição
      i += 4;
    } else {
      // Copiar símbolo AMI normal
      result[i] = raw[i];
      if (raw[i] != 0) {
        lastNonZeroPol = raw[i];
        nonZeroSinceLast++;
      }
      i++;
    }
  }

  memcpy(out, result, len * sizeof(int8_t));
  outLen = len;
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"error\":\"ESP-NOW init failed\"}");
    return;
  }
  esp_now_register_send_cb(onSent);

  // Registrar peers
  esp_now_peer_info_t peerInfo = {};
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  memcpy(peerInfo.peer_addr, SLAVE_1_MAC, 6);
  esp_now_add_peer(&peerInfo);

  memcpy(peerInfo.peer_addr, SLAVE_2_MAC, 6);
  esp_now_add_peer(&peerInfo);

  Serial.println("{\"status\":\"master_ready\"}");
}

// ── Loop ───────────────────────────────────────────────────────────────────
void loop() {
  if (!Serial.available()) return;

  String json = Serial.readStringUntil('\n');
  json.trim();
  if (json.length() == 0) return;

  // Parse JSON
  StaticJsonDocument<1024> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) {
    Serial.println("{\"error\":\"json_parse\"}");
    return;
  }

  const char *bitsStr = doc["bits"] | "";
  uint8_t key         = doc["key"]  | 0;
  const char *orig    = doc["original"] | "";

  uint16_t len = strlen(bitsStr);
  if (len == 0 || len > MAX_BITS) {
    Serial.println("{\"error\":\"invalid_bits\"}");
    return;
  }

  // Converter string de bits para array
  uint8_t bits[MAX_BITS];
  for (uint16_t i = 0; i < len; i++) {
    bits[i] = (bitsStr[i] == '1') ? 1 : 0;
  }

  // Codificar HDB3
  memset(&outMsg, 0, sizeof(outMsg));
  encodeHDB3(bits, len, outMsg.hdb3, outMsg.len);
  outMsg.key = key;
  strncpy(outMsg.original, orig, 127);

  // Enviar via ESP-NOW
  deliveredCount = 0;
  esp_now_send(SLAVE_1_MAC, (uint8_t*)&outMsg, sizeof(outMsg));
  esp_now_send(SLAVE_2_MAC, (uint8_t*)&outMsg, sizeof(outMsg));

  // Aguardar callbacks (máx 500ms)
  unsigned long t = millis();
  while (millis() - t < 500) delay(10);

  // Retornar resultado para o PC
  StaticJsonDocument<256> resp;
  resp["delivered"] = deliveredCount;
  resp["slaves"]    = totalSlaves;
  resp["hdb3_len"]  = outMsg.len;

  // Serializar HDB3 para o PC visualizar
  String hdb3str = "[";
  for (uint16_t i = 0; i < outMsg.len; i++) {
    hdb3str += String(outMsg.hdb3[i]);
    if (i < outMsg.len - 1) hdb3str += ",";
  }
  hdb3str += "]";
  resp["hdb3"] = serialized(hdb3str);

  String out;
  serializeJson(resp, out);
  Serial.println(out);
}
