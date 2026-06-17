# HDB3 Line Coding — Trabalho de Redes
## Comunicação ESP-NOW com 3× ESP32 + Interface Python

---

## Visão Geral

Este projeto implementa a codificação de linha **HDB3 (High-Density Bipolar 3-zero substitution)**
em um sistema distribuído real, composto por três ESP32 se comunicando via **ESP-NOW** (protocolo
de rádio peer-to-peer da Espressif, sem roteador Wi-Fi) e uma interface gráfica desktop em Python
que roda no PC.

O fluxo completo do sistema cobre todas as exigências do trabalho (T1 a T8):

```
[HOST A — PC]                     [ESP32 MASTER]           [ESP32 SLAVE 1/2]           [HOST B — PC]
  Digita mensagem
  → XOR encrypt (T4)
  → ASCII → binário (T5)
  → HDB3 encode (T6)      →Serial→  recebe bits
  → mostra gráfico (T2)             HDB3 encode
  → envia via serial (T7)           envia ESP-NOW   →ESP-NOW→  recebe pacote
                                                               HDB3 decode (T8)
                                                               XOR decrypt  (T8)
                                                               envia Serial
                                                    ←Serial←  resultado
  recebe resultado
  → mostra gráfico (T2)
  → mostra msg (T1/T8)
```

---

## Arquitetura de Hardware

```
PC (USB)──────────────────────────[ESP32 MASTER]
                                       │  ESP-NOW 2.4 GHz (sem roteador)
                              ┌────────┴────────┐
                         [ESP32 SLAVE 1]   [ESP32 SLAVE 2]
                              │                 │
                           USB (PC)          USB (PC ou outro PC)
```

- O **Master** é o Host A: recebe a mensagem do PC, codifica em HDB3 e transmite via rádio.
- Os **Slaves** são o Host B: recebem o sinal HDB3, decodificam e devolvem o texto ao PC.
- A comunicação entre ESP32s usa **ESP-NOW**, que é um protocolo proprietário da Espressif
  baseado em IEEE 802.11 mas sem necessidade de roteador ou ponto de acesso — funciona
  diretamente de dispositivo para dispositivo, como um Bluetooth simplificado.

---

## Algoritmo HDB3

### O que é

HDB3 é uma variação do AMI (Alternate Mark Inversion) que resolve o problema de longas
sequências de zeros. No AMI puro, uma sequência de zeros não gera transições de sinal,
o que dificulta a sincronização de clock no receptor. O HDB3 substitui grupos de 4 zeros
consecutivos por sequências especiais que introduzem transições controladas.

### Símbolos

O sinal HDB3 trabalha com três níveis de tensão:
- **+1** — pulso positivo
- ** 0** — ausência de sinal
- **-1** — pulso negativo

### Regra AMI de base

Antes de aplicar o HDB3, a sequência de bits é primeiro convertida para AMI:
- Bit **0** → símbolo **0** (sem pulso)
- Bit **1** → símbolo alternado: **+1, -1, +1, -1, ...** (cada 1 inverte a polaridade)

### Substituição HDB3

Toda vez que aparecem **4 zeros consecutivos**, eles são substituídos por uma de duas
sequências especiais. A escolha depende de quantos pulsos não-zero ocorreram desde
a **última substituição**:

| Pulsos não-zero desde última substituição | Substituição aplicada |
|---|---|
| **Ímpar** | `0 0 0 V` |
| **Par** | `B 0 0 V` |

Onde:
- **V (Violation):** pulso com a **mesma polaridade** do último pulso não-zero — isso viola
  a regra AMI propositalmente, servindo como marcador para o receptor identificar a substituição.
- **B (Bipolar):** pulso que **segue a regra AMI** normalmente (polaridade oposta ao último).
  Existe para manter o equilíbrio DC do sinal.

### Exemplo prático

```
Bits de entrada:   1  0  0  0  0  0  0  0  1  1
AMI raw:          +1  0  0  0  0  0  0  0 -1 +1
                      └────────────┘ └──────────┘
                        grupo de 8 zeros = 2× grupos de 4

Após HDB3:        +1  0  0  0 +V  -B  0  0 -V -1 +1
                      └─000V─┘ └──B00V──┘
                   (1 pulso antes → ímpar → 000V)
                   (após V, count=0 → par → B00V)
```

### Decodificação (processo inverso)

O receptor percorre o sinal HDB3 procurando **violações AMI** (pulso com mesma polaridade
do anterior). Ao encontrar uma violação V:
- Se os 3 símbolos anteriores forem zero → era `000V` → substituir os 4 por zeros
- Se o símbolo 3 posições antes for não-zero → era `B00V` → zerar aquele B e o V

Depois de remover todas as substituições, cada símbolo não-zero vira bit 1 e cada zero
vira bit 0.

---

## Criptografia XOR

### Como funciona

A criptografia usada é o **XOR simétrico byte a byte**. Cada caractere da mensagem tem
seu valor ASCII calculado com XOR em relação a uma chave numérica (0–255):

```
Cifrar:    char_original XOR key  →  char_cifrado
Decifrar:  char_cifrado  XOR key  →  char_original
```

A operação XOR é auto-inversa: aplicar duas vezes com a mesma chave retorna o valor original.
Por isso a mesma função serve para cifrar e decifrar.

### Por que XOR

- Implementação trivial no ESP32 (operação nativa de 1 ciclo de clock)
- Não depende de bibliotecas externas
- Funciona com ASCII estendido (qualquer byte 0–255)
- Mantém o mesmo comprimento da mensagem original

### Exemplo

```
Mensagem:   'A'  'B'  'C'
ASCII:       65   66   67
XOR 42:     123   88   89   ← cifrado
XOR 42:      65   66   67   ← decifrado (original)
```

---

## Conversão ASCII Estendido → Binário

Cada caractere da mensagem (já criptografada) é convertido para seu valor ASCII e
representado em **8 bits** (1 byte por caractere). Isso garante suporte a letras
especiais e acentuadas (á, ã, ç, etc.) que estão na tabela ASCII estendida (128–255).

```
'H' = 72  = 0 1 0 0 1 0 0 0
'i' = 105 = 0 1 1 0 1 0 0 1
'!' = 33  = 0 0 1 0 0 0 0 1
```

---

## Estrutura dos Arquivos

```
esp32_master/
  esp32_master.ino     Firmware do ESP32 Master

esp32_slave/
  esp32_slave.ino      Firmware dos ESP32 Slaves (mesmo arquivo para ambos)

interface_pc/
  interface.py         Interface gráfica Python (roda no PC)

README.md              Este arquivo
```

---

## Firmware ESP32 Master (`esp32_master.ino`)

### Responsabilidades
1. Inicializar ESP-NOW e registrar os dois Slaves como peers
2. Aguardar JSON do PC via Serial (`{"bits":"010100...", "key":42, "original":"Oi"}`)
3. Converter string de bits para array de uint8
4. Executar o encoder HDB3 completo
5. Montar struct `esp_now_msg_t` com o sinal HDB3, chave e comprimento
6. Enviar para Slave 1 e Slave 2 via `esp_now_send()`
7. Aguardar callbacks de confirmação de entrega
8. Retornar JSON ao PC com resultado (`{"delivered":2, "hdb3":[...], "hdb3_len":80}`)

### Struct de comunicação ESP-NOW

```cpp
typedef struct {
  int8_t   hdb3[512];   // sinal HDB3: valores -1, 0 ou +1
  uint16_t len;          // número de símbolos no sinal
  uint8_t  key;         // chave XOR para o Slave decifrar
  char     original[128]; // texto original (debug)
} esp_now_msg_t;
```

### Encoder HDB3 no firmware

O encoder opera em dois passos:
1. **AMI raw:** percorre os bits, alternando polaridade a cada bit 1
2. **Substituição HDB3:** varre o array procurando grupos de 4 zeros, aplica
   000V ou B00V conforme o contador de pulsos não-zero, atualiza o contador
   e a última polaridade

---

## Firmware ESP32 Slave (`esp32_slave.ino`)

### Responsabilidades
1. Inicializar ESP-NOW e registrar callback de recepção
2. Ao receber pacote, copiar struct `esp_now_msg_t`
3. Executar decoder HDB3: identificar violações, remover substituições, converter para bits
4. Agrupar bits em bytes e aplicar XOR decrypt com a chave recebida
5. Enviar resultado ao PC via Serial em JSON

### Decoder HDB3 no firmware

1. Percorre o sinal procurando violações (pulso com mesma polaridade do anterior)
2. Ao encontrar V, inspeciona os 3 símbolos anteriores para determinar se era 000V ou B00V
3. Zera os símbolos correspondentes à substituição
4. Converte o sinal limpo: não-zero → 1, zero → 0

**Observação:** O mesmo sketch `esp32_slave.ino` é gravado nos dois Slaves. Cada um
processará o sinal de forma independente e enviará o resultado ao PC via sua porta Serial.

---

## Interface Python (`interface.py`)

### Bibliotecas utilizadas (todas open source)

| Biblioteca | Licença | Finalidade |
|---|---|---|
| `customtkinter` | MIT | Widgets modernos sobre tkinter |
| `tkinter` | Python built-in | Base da interface |
| `matplotlib` | PSF | Gráficos de forma de onda |
| `pyserial` | BSD | Comunicação USB Serial |
| `json` | built-in | Serialização do protocolo |
| `threading` | built-in | Leitura Serial em background |

### Componentes da interface

#### Painel esquerdo — Controles e pipeline

- **Conexão Serial:** seleção de porta COM do Master e do Slave, botão conectar
- **Host A — Envio:** campo de texto para a mensagem, campo para chave XOR, botão enviar
- **Pipeline de transformação (T1):** quatro campos somente-leitura exibindo em tempo real:
  - Mensagem original
  - Mensagem criptografada (XOR)
  - Binário ASCII estendido
  - Símbolos HDB3 (sequência de -1, 0, +1)
- **Host B — Recepção:** três campos exibindo o que chegou do Slave:
  - HDB3 recebido
  - Bits após decodificação
  - Mensagem recuperada (texto final)

#### Painel direito — Gráficos (T2)

Dois gráficos matplotlib lado a lado (verticalmente):
- **Host A:** forma de onda HDB3 do sinal transmitido
- **Host B:** forma de onda HDB3 do sinal recebido

Cada gráfico usa três cores para distinguir os símbolos:
- Verde (`#00d4aa`) → +1
- Vermelho (`#ff6b6b`) → -1
- Cinza (`#4a4a6a`) → 0

Violações são anotadas com a letra **V** em amarelo diretamente no gráfico.

#### Modo demo (sem hardware)

Se o botão **Processar & Enviar** for clicado sem ESP32 conectado, a interface detecta
a ausência de Serial e executa toda a cadeia localmente em Python — útil para apresentar
a lógica HDB3 e o visual sem precisar do hardware.

---

## Instalação e Configuração

### 1. Instalar dependências Python

```bash
pip install customtkinter pyserial matplotlib
```

### 2. Descobrir MACs dos ESP32

Gravar este sketch temporário em cada ESP32:

```cpp
#include <WiFi.h>
void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  Serial.println(WiFi.macAddress());
}
void loop() {}
```

Abrir o Serial Monitor e anotar o MAC de cada placa.

### 3. Atualizar MACs no código

**`esp32_master.ino`** — linhas 22-23:
```cpp
uint8_t SLAVE_1_MAC[] = {0xXX, 0xXX, 0xXX, 0xXX, 0xXX, 0xXX};
uint8_t SLAVE_2_MAC[] = {0xXX, 0xXX, 0xXX, 0xXX, 0xXX, 0xXX};
```

**`esp32_slave.ino`** — linha 23:
```cpp
uint8_t MASTER_MAC[] = {0xXX, 0xXX, 0xXX, 0xXX, 0xXX, 0xXX};
```

### 4. Instalar bibliotecas no Arduino IDE

- Abrir **Tools → Manage Libraries**
- Instalar: **ArduinoJson** by Benoit Blanchon (versão 6.x)
- `esp_now` e `WiFi` já vêm incluídas no core ESP32

### 5. Gravar firmwares

- Gravar `esp32_master.ino` na placa designada como Master
- Gravar `esp32_slave.ino` nos dois Slaves (mesmo arquivo, mesmo sketch)

### 6. Conectar ao PC e executar

```bash
python interface.py
```

---

## Protocolo Serial (PC ↔ ESP32)

### PC → Master (JSON, terminado em `\n`)
```json
{"bits": "0100100001101001", "key": 42, "original": "Hi"}
```

### Master → PC (resposta após envio ESP-NOW)
```json
{"delivered": 2, "slaves": 2, "hdb3_len": 16, "hdb3": [0,1,0,0,...]}
```

### Slave → PC (ao receber do Master)
```json
{"type": "received", "hdb3": [0,1,0,...], "bits": "0100100001101001", "decoded": "Hi", "key": 42}
```

---

## Checklist de Critérios (T1–T8)

| Critério | Implementado em | Status |
|---|---|---|
| T1 — Interface gráfica com todos os campos | `interface.py` | ✓ |
| T2 — Forma de onda em ambos os lados | `interface.py` (matplotlib) | ✓ |
| T3 — Comunicação entre computadores | ESP-NOW (Master ↔ Slaves) | ✓ |
| T4 — Criptografia | XOR simétrico em `interface.py` e `.ino` | ✓ |
| T5 — ASCII estendido → binário | `text_to_binary()` em `interface.py` | ✓ |
| T6 — Aplicação do algoritmo HDB3 | `encode_hdb3()` em `interface.py` + `encodeHDB3()` no Master | ✓ |
| T7 — Envio pela rede | ESP-NOW via `esp_now_send()` | ✓ |
| T8 — Processo inverso no receptor | `decode_hdb3()` no Slave + `interface.py` | ✓ |

---

## Observações para a apresentação

- O professor pediu para testar com a **sequência binária da aula** sem criptografia:
  basta colocar a chave XOR como **0** (zero) — o XOR com 0 não altera os dados.
- Os gráficos de forma de onda aparecem automaticamente tanto no Host A quanto no Host B
  assim que a mensagem é enviada e recebida.
- O modo demo funciona sem hardware caso seja necessário apresentar a lógica em sala.
