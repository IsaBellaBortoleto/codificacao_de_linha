# Codificação de Linha HDB3 — Trabalho de Comunicação de Dados

## Comunicação entre computadores via ESP32 + ESP-NOW, com interface Python

UTFPR Curitiba — Comunicação de Dados
Algoritmo sorteado para a equipe: **HDB3** (item 11 da lista de algoritmos)

---

## Visão Geral

Este projeto implementa a codificação de linha **HDB3 (High-Density Bipolar 3-zero
substitution)** num sistema de comunicação real entre **vários computadores** — **dois
emissores** e **um servidor receptor** — usando **três ESP32** como rádios de enlace
(protocolo **ESP-NOW**, peer-to-peer, sem roteador Wi-Fi) e uma **interface gráfica
desktop em Python**.

A topologia é **2 Slaves → 1 Master**: cada emissor tem uma ESP32 **Slave** e o servidor
tem uma ESP32 **Master** que recebe os dois.

Decisão de arquitetura importante: **todo o processamento é feito no PC, em Python.**
Os ESP32 funcionam apenas como **rádios repassadores** — não fazem HDB3, XOR nem
conversão ASCII. Isso mantém a lógica do trabalho num só lugar (fácil de demonstrar e
depurar) e usa o ESP-NOW só como "fio sem fio" entre as máquinas.

```
[ PC Emissor (Slave 1 ou 2) ]                          [ Servidor — Receptor ]
 digita o texto                                          mostra o texto recuperado
 → XOR encrypt        (Python)                           ↑ XOR decrypt        (Python)
 → ASCII → binário    (Python)                           ↑ binário → ASCII    (Python)
 → HDB3 encode        (Python)                           ↑ HDB3 decode        (Python)
 → mostra gráfico                                        ↑ mostra gráfico
 → manda string HDB3 pela USB                            ↑ recebe string HDB3 pela USB
        │                                                       │
   USB Serial                                              USB Serial
        ▼                                                       ▲
  [ ESP32 SLAVE 1/2 ] ─────── ESP-NOW (rádio 2.4 GHz) ───►  [ ESP32 MASTER ]
   repassa os bytes                                         repassa os bytes
```

O que cruza a rede é apenas a **string do sinal HDB3** (caracteres `+`, `-`, `0`).
A **chave XOR não é transmitida**: cada operador digita a mesma chave na sua interface
(segredo combinado fora da banda).

---

## Requisitos do trabalho (T1–T8) e onde estão implementados

| Critério | Descrição | Onde | Status |
|---|---|---|---|
| **T1** | Interface gráfica: texto, texto criptografado, binário, sinal do algoritmo e gráfico | [`interface.py`](interface.py) (aba *Emissão*) | ✅ |
| **T2** | Forma de onda em ambos os lados (montagem e processo inverso) | [`interface.py`](interface.py) — gráficos de Emissão e Recepção (matplotlib) | ✅ |
| **T3** | Comunicação entre dois ou mais computadores (sem localhost) | ESP-NOW entre Slave ↔ Master (`.ino`) | ✅ |
| **T4** | Criptografia | XOR cíclico em [`crypto.py`](crypto.py) | ✅ |
| **T5** | Texto → binário via tabela ASCII estendido (acentos) | `texto_para_binario()` em [`ascii.py`](ascii.py) | ✅ |
| **T6** | Aplicação do princípio do algoritmo (HDB3) | `encode_hdb3()` em [`encode.py`](encode.py) | ✅ |
| **T7** | Envio pela rede | `esp_now_send()` em [`esp32_slave.ino`](esp32_slave.ino) | ✅ |
| **T8** | Processo inverso no receptor até reconhecer a mensagem | `decode_hdb3()` em [`decode.py`](decode.py) + recepção em [`interface.py`](interface.py) | ✅ |

**Exigências gerais:** linguagem desktop (Python) ✅ · comunicação entre máquinas, não
localhost (rádio ESP-NOW) ✅ · criptografia estudada e documentada (XOR, ver seção
abaixo) ✅ · mecanismo de comunicação implementado pela própria equipe no firmware, não
um serviço externo ✅.

---

## Arquitetura de hardware

São **três ESP32**: duas **Slaves** (uma em cada PC emissor) e uma **Master** (no
servidor receptor). As duas Slaves transmitem para a mesma Master via ESP-NOW.

```
                    [ Servidor — Receptor (PC) ]
                              │ USB Serial
                       [ ESP32 MASTER ]        ← Host B
                              ▲
                              │  ESP-NOW (rádio 2.4 GHz)
                ┌─────────────┴─────────────┐
                │                           │
         [ ESP32 SLAVE 1 ]           [ ESP32 SLAVE 2 ]   ← Host A
                │ USB                       │ USB
        [ PC Emissor 1 ]            [ PC Emissor 2 ]
```

- **ESP32 Slave 1 e Slave 2** = lado do **Host A (emissores)**: cada uma recebe a string
  HDB3 do seu PC pela Serial e a transmite via ESP-NOW para a Master.
- **ESP32 Master** = lado do **Host B (receptor)**: aceita pacotes de **qualquer** Slave
  e os repassa ao servidor pela Serial. O JSON do Master inclui o campo `from` com o MAC
  da Slave de origem, então dá para saber qual emissor enviou.
- O enlace **ESP-NOW** é um protocolo da Espressif baseado em 802.11, porém sem
  roteador ou ponto de acesso — dispositivo a dispositivo. É isso que garante que a
  comunicação **não é localhost**: os computadores estão fisicamente separados, ligados
  por rádio.

> Na aba *Emissão*, o operador escolhe **Slave 1** ou **Slave 2** (cada uma com sua porta
> COM). As duas Slaves rodam o **mesmo** firmware [`esp32_slave.ino`](esp32_slave.ino) —
> basta gravá-lo nas duas placas, ambas apontando para o MAC da Master.

---

## Fluxo de dados (passo a passo)

**Host A — Emissão** (aba *Emissão*):
1. Operador digita o texto e a chave XOR.
2. `processar_emissao()` ([`pipeline.py`](pipeline.py)) executa em Python:
   `texto → XOR (criptografar) → binário ASCII estendido → encode_hdb3`.
3. A interface preenche os campos (texto, texto criptografado, binário original,
   binário criptografado, símbolos HDB3) e desenha a forma de onda.
4. Ao clicar **Enviar para ESP**, o PC manda pela Serial ao Slave o JSON
   `{"type":"send","hdb3":"...","len":N}`; o Slave repassa via ESP-NOW.

**Host B — Recepção** (aba *Recepção*):
1. Operador seleciona a porta do Master e digita a **mesma** chave XOR.
2. Ao receber o pacote, o Master entrega ao PC `{"from":MAC,"payload":"..."}`.
3. `processar_recepcao()` executa o caminho inverso em Python:
   `HDB3 → decode_hdb3 → binário → ASCII → texto criptografado → XOR (descriptografar)`.
4. A interface mostra HDB3 recebido, bits decodificados, texto criptografado, texto
   original e desenha a forma de onda recebida.

---

## Algoritmo HDB3

### O que é

HDB3 é uma variação do AMI (Alternate Mark Inversion) que resolve o problema de longas
sequências de zeros. No AMI puro, uma sequência de zeros não gera transições de sinal, o
que dificulta a sincronização de clock no receptor. O HDB3 substitui grupos de **4 zeros
consecutivos** por sequências especiais que introduzem transições controladas.

### Símbolos

Três níveis de tensão: **+1** (pulso positivo), **0** (sem sinal) e **-1** (pulso negativo).

### Regra AMI de base

- Bit **0** → símbolo **0**.
- Bit **1** → polaridade alternada **+1, -1, +1, -1, …** (cada 1 inverte a polaridade).

### Substituição HDB3

A cada 4 zeros consecutivos, aplica-se uma de duas substituições, conforme o número de
pulsos não-zero desde a **última substituição**:

| Pulsos não-zero desde a última substituição | Substituição |
|---|---|
| **Ímpar** | `0 0 0 V` |
| **Par** | `B 0 0 V` |

- **V (violação):** pulso com a **mesma polaridade** do último pulso — viola a regra AMI
  de propósito, servindo de marcador para o receptor.
- **B (bipolar):** pulso que **segue a regra AMI** (polaridade oposta), para manter o
  equilíbrio DC.

### Exemplo verificado (sequência da aula — Figura 4.20 do material)

```
Bits:   1  1  0 0 0 0   1   0 0 0 0   0 0 0 0   0
HDB3:   +  -  + 0 0 +   -   0 0 0 -   + 0 0 +   0
              └─B00V─┘      └─000V─┘  └─B00V─┘
              (par)         (ímpar)   (par)
```

Esse é exatamente o resultado produzido por `encode_hdb3()` e bate símbolo a símbolo com
a Figura 4.20 da aula (ver seção *Teste de validação*).

### Decodificação (processo inverso)

O receptor procura **violações AMI** (pulso com a mesma polaridade do anterior). Ao achar
um V:
- 3 símbolos anteriores zero → era `000V` → zera os 4;
- símbolo 3 posições antes não-zero → era `B00V` → zera o B e o V.

Depois de remover as substituições, cada não-zero vira bit 1 e cada zero vira bit 0.

---

## Criptografia XOR

### Como funciona

Usa-se **XOR simétrico** com uma chave de texto cíclica (padrão: `"internet explorer"`).
Cada caractere é combinado por XOR com o caractere correspondente da chave; quando a
mensagem é maior que a chave, a chave se repete (`i % len(chave)`).

```
Cifrar:    char XOR chave  →  char_cifrado
Decifrar:  char_cifrado XOR chave  →  char
```

O XOR é seu próprio inverso, então a mesma função cifra e decifra
([`crypto.py`](crypto.py): `criptografar` / `descriptografar`).

### Por que XOR

- Simples, sem bibliotecas externas; opera byte a byte (qualquer valor 0–255).
- Mantém o comprimento da mensagem.
- A **chave não trafega na rede**: os dois lados a digitam na interface. Para testar a
  sequência da aula **sem criptografia**, ver a seção *Teste de validação*.

---

## Conversão ASCII Estendido → Binário

Cada caractere é convertido para seu valor numérico e representado em **8 bits**
(latin-1 / ISO-8859-1), o que cobre acentos (á, ã, ç, etc., valores 128–255).
Caracteres Unicode fora de 0–255 (como —, €, emojis) são **rejeitados** com erro claro
([`ascii.py`](ascii.py): `texto_para_binario`, `binario_para_texto`, `validar_texto`).

```
'H' = 72  = 01001000
'ã' = 227 = 11100011
```

---

## Estrutura dos arquivos

```
codificacao_de_linha/
├── interface.py        Interface gráfica (Tkinter + matplotlib) — roda no PC
├── pipeline.py         Cola entre GUI, algoritmos e Serial; monta/lê payloads
├── encode.py           encode_hdb3()  — codificador HDB3
├── decode.py           decode_hdb3()  — decodificador HDB3
├── ascii.py            Conversão texto ↔ binário (ASCII estendido)
├── crypto.py           Criptografia XOR
├── esp32_slave.ino     Firmware do ESP32 transmissor (relay PC→ESP-NOW)
├── esp32_master.ino    Firmware do ESP32 receptor (relay ESP-NOW→PC)
├── exemploDeUso.md     Exemplo mínimo de uso do encoder/decoder
└── README.md           Este arquivo
```

---

## Firmware ESP32

Os dois firmwares são **apenas repassadores** — nenhum processamento de HDB3/XOR/ASCII
acontece no ESP32.

### `esp32_slave.ino` — transmissor (lado do Host A)

1. Inicializa ESP-NOW e registra o Master como peer (`MASTER_MAC`).
2. Lê do PC, pela Serial, uma linha terminada em `\n`.
3. Envia esses bytes crus via `esp_now_send()` ao Master.
4. Responde ao PC `{"status":"sent"}` ou `{"status":"failed"}`.

> **Atualize `MASTER_MAC`** (linha 26) com o MAC real do seu Master.

### `esp32_master.ino` — receptor (lado do Host B)

1. Inicializa ESP-NOW e registra o callback de recepção (aceita qualquer peer).
2. Ao receber um pacote, monta `{"from":"<MAC>","payload":"<dados>"}` e envia ao PC
   pela Serial.

Limite de payload ESP-NOW: **250 bytes** por pacote.

---

## Interface Python (`interface.py`)

### Bibliotecas

| Biblioteca | Uso |
|---|---|
| `tkinter` / `ttk` / `ScrolledText` | base da interface (built-in do Python) |
| `matplotlib` | gráficos de forma de onda |
| `pyserial` | comunicação USB Serial (em `pipeline.py`) |
| `threading`, `json`, `ast` | leitura serial em background e serialização (built-in) |

### Layout

Duas abas:

**Aba *Emissão***
- Campos: *Texto original*, *Chave XOR* (padrão `internet explorer`), seleção de
  *Slave* (1/2), *Porta Slave 1*, *Porta Slave 2*.
- Botões: *Atualizar portas*, *Processar*, *Enviar para ESP*.
- Sub-abas de saída: **Texto** (original / criptografado), **Binários** (original /
  criptografado), **HDB3** (sequência de símbolos).
- Gráfico *Sinal HDB3 — emissão*.

**Aba *Recepção***
- Campos: *Porta ESP master*, *Chave XOR*.
- Botões: *Atualizar portas*, *Iniciar recepção*, *Parar*.
- Saída: *HDB3 recebido*, *Bits decodificados*, *Texto criptografado*, *Texto original*.
- Gráfico *Sinal HDB3 — recepção*.

### Processar sem hardware

O botão **Processar** executa toda a cadeia de emissão localmente em Python (XOR → ASCII
→ HDB3) e desenha a forma de onda **sem precisar de ESP32 conectado** — útil para
conferir a lógica e o gráfico. O *envio* e a *recepção* completos (ciclo entre os dois
PCs) exigem o hardware conectado.

---

## Protocolo Serial / ESP-NOW

**PC A → Slave** (Serial, linha terminada em `\n`):
```json
{"type":"send","hdb3":"00+00-+000+00-+-","len":16}
```

**Slave → PC A** (confirmação de envio):
```json
{"status":"sent"}
```

**Master → PC B** (ao receber pelo rádio):
```json
{"from":"AA:BB:CC:DD:EE:FF","payload":"{\"type\":\"send\",\"hdb3\":\"...\",\"len\":16}"}
```

O `hdb3` é a string de símbolos (`+`, `-`, `0`). A chave XOR **não** aparece no
protocolo.

---

## Instalação e execução

### 1. Dependências Python
```bash
pip install pyserial matplotlib
```
(`tkinter` já vem com o Python; no Linux pode ser `sudo apt install python3-tk`.)

### 2. Descobrir o MAC dos ESP32
Grave um sketch temporário em cada placa e leia o Serial Monitor:
```cpp
#include <WiFi.h>
void setup(){ Serial.begin(115200); WiFi.mode(WIFI_STA); Serial.println(WiFi.macAddress()); }
void loop(){}
```

### 3. Configurar e gravar os firmwares
- Em [`esp32_slave.ino`](esp32_slave.ino), atualize `MASTER_MAC` com o MAC do Master.
- Grave `esp32_slave.ino` nas **duas placas Slave** (mesmo sketch nas duas) e
  `esp32_master.ino` na placa Master (servidor).
- No Arduino IDE, `WiFi` e `esp_now` já vêm no core ESP32.

### 4. Rodar a interface (em cada PC)
```bash
python interface.py
```

---

## Teste de validação (sequência da aula, sem criptografia)

O professor pede para validar com a **sequência binária da aula sem criptografia**. Para
o HDB3, essa sequência é a da **Figura 4.20** do material:

```
1 1 0 0 0 0 1 0 0 0 0 0 0 0 0 0   →   1100001000000000
```

Como a interface hoje recebe **texto** (e aplica XOR + ASCII antes do HDB3), a forma
mais direta de validar a camada de linha pura é rodar os módulos do algoritmo:

```python
from encode import encode_hdb3
from decode import decode_hdb3

bits = [1,1,0,0,0,0,1,0,0,0,0,0,0,0,0,0]
sinal = encode_hdb3(bits)          # + - + 0 0 + - 0 0 0 - + 0 0 + 0
print(sinal)
print(decode_hdb3(sinal) == bits)  # True  → bits entram = bits saem
```

O resultado bate símbolo a símbolo com a Figura 4.20.

> **Limitação conhecida:** ainda não há, na interface gráfica, um campo para colar uma
> sequência binária crua nem uma opção de "sem criptografia" (a chave XOR é sempre
> aplicada; uma chave vazia é rejeitada). Esse teste, hoje, é feito pelos módulos acima.

---

## Limitações conhecidas

- **Entrada só por texto:** não há campo de entrada binária direta nem modo "sem
  criptografia" na GUI (ver seção anterior).
- **Tamanho da mensagem:** o envio é limitado a `MAX_SIMBOLOS_HDB3 = 200` símbolos
  ([`pipeline.py`](pipeline.py)) e a 250 bytes por pacote ESP-NOW — na prática, ~25
  caracteres por mensagem.
- **Gráfico simples:** a forma de onda é desenhada em uma cor só (`steps-post`), sem
  destacar os símbolos B/V com cores ou rótulos.
- **Caracteres Unicode** fora de 0–255 (—, €, emojis) são rejeitados por não caberem no
  ASCII estendido.


## ⚠️ Disclaimer

Na primeira execução no **Windows**, ao tentar enviar ou receber dados, pode aparecer uma mensagem de erro. Isso é normal e não indica um problema real — **basta ignorar a mensagem e tentar novamente**. Os dados serão processados corretamente na segunda tentativa.

Essas instabilidades **não ocorrem no Linux**, onde a comunicação funciona de forma estável desde a primeira execução.