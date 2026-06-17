/*
 * ESP32 SLAVE - HDB3 Decoder
 * Trabalho de Codificação de Linha
 *
 * Recebe mensagem HDB3 via ESP-NOW do Master.
 * Decodifica → binário → XOR → ASCII → envia ao PC via Serial.
 *
 * IMPORTANTE: Atualize MASTER_MAC com o MAC do seu ESP32 Master.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <ArduinoJson.h>

// ── MAC do Master (atualize!) ──────────────────────────────────────────────
uint8_t MASTER_MAC[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x00};

#define MAX_BITS 512

typedef struct {
  int8_t  hdb3[MAX_BITS];
  uint16_t len;
  uint8_t  key;
  char     original[128];
} esp_now_msg_t;

// ── HDB3 Decoder ──────────────────────────────────────────────────────────
/*
 * Decodificação HDB3:
 * Percorre o sinal procurando violações AMI (V).
 * Uma violação é um pulso com a mesma polaridade do pulso não-zero anterior.
 *
 * Ao encontrar ...0,0,0,V ou B,0,0,V → substituir os 4 por zeros.
 * O restante: pulso não-zero → bit 1, zero → bit 0.
 */
void decodeHDB3(const int8_t *hdb3, uint16_t len, uint8_t *bits) {
  // Passo 1: identificar e remover substituições HDB3
  int8_t temp[MAX_BITS];
  memcpy(temp, hdb3, len * sizeof(int8_t));

  int lastPol = 0;  // polaridade do último pulso não-zero

  for (uint16_t i = 0; i < len; i++) {
    if (temp[i] == 0) continue;

    // Verificar violação: mesmo sinal do anterior
    if (lastPol != 0 && temp[i] == lastPol) {
      // É um V — encontrar início da substituição (4 posições atrás)
      // Caso 000V: 3 zeros antes de i
      // Caso B00V: B em i-3, zeros em i-2 e i-1
      if (i >= 3) {
        bool case000V = (temp[i-1] == 0 && temp[i-2] == 0 && temp[i-3] == 0);
        bool caseB00V = (temp[i-1] == 0 && temp[i-2] == 0 && temp[i-3] != 0);

        if (case000V) {
          temp[i] = 0;
        } else if (caseB00V) {
          temp[i-3] = 0;
          temp[i]   = 0;
        }
      }
      // lastPol não muda (o V foi removido)
    } else {
      lastPol = temp[i];
    }
  }

  // Passo 2: converter AMI → bits
  for (uint16_t i = 0; i < len; i++) {
    bits[i] = (temp[i] != 0) ? 1 : 0;
  }
}

// ── XOR Decrypt ───────────────────────────────────────────────────────────
// Operação XOR bit a bit nos bytes; revertível com mesma chave
String xorDecrypt(const uint8_t *bits, uint16_t len, uint8_t key) {
  // Agrupar bits em bytes
  String result = "";
  for (uint16_t i = 0; i + 7 < len; i += 8) {
    uint8_t byte_val = 0;
    for (int b = 0; b < 8; b++) {
      byte_val = (byte_val << 1) | bits[i + b];
    }
    byte_val ^= key;  // XOR decrypt
    if (byte_val > 0) result += (char)byte_val;
  }
  return result;
}

// ── Callback ESP-NOW ───────────────────────────────────────────────────────
void onReceive(const uint8_t *mac, const uint8_t *data, int len) {
  if (len != sizeof(esp_now_msg_t)) return;

  esp_now_msg_t msg;
  memcpy(&msg, data, sizeof(msg));

  // Decodificar HDB3
  uint8_t bits[MAX_BITS] = {0};
  decodeHDB3(msg.hdb3, msg.len, bits);

  // Descriptografar
  String decoded = xorDecrypt(bits, msg.len, msg.key);

  // Serializar HDB3 para envio ao PC
  String hdb3str = "[";
  for (uint16_t i = 0; i < msg.len; i++) {
    hdb3str += String(msg.hdb3[i]);
    if (i < msg.len - 1) hdb3str += ",";
  }
  hdb3str += "]";

  // Montar bits string decodificada
  String bitsStr = "";
  for (uint16_t i = 0; i < msg.len; i++) bitsStr += String(bits[i]);

  // Enviar resultado ao PC via Serial
  StaticJsonDocument<1024> doc;
  doc["type"]    = "received";
  doc["hdb3"]    = serialized(hdb3str);
  doc["bits"]    = bitsStr;
  doc["decoded"] = decoded;
  doc["key"]     = msg.key;

  String out;
  serializeJson(doc, out);
  Serial.println(out);
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("{\"error\":\"ESP-NOW init\"}");
    return;
  }
  esp_now_register_recv_cb(onReceive);

  // Registrar Master como peer (necessário para ACK)
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
