# 📡 LineCode HDB3 — Comunicação de Dados · UTFPR

Trabalho de implementação de **codificação de linha HDB3** para a disciplina de Comunicação de Dados (Prof. Hermes Irineu Del Monego), desenvolvido em Python com interface gráfica, criptografia e comunicação em rede real entre computadores.

---

## 📋 Sobre o projeto

O aplicativo simula a transmissão digital de mensagens entre dois computadores, seguindo o pipeline completo de uma camada física digital:

```
[Host A — Emissor]
  Mensagem de texto
      ↓ Criptografia
      ↓ Conversão ASCII Estendido → Binário
      ↓ Codificação HDB3
      ↓ Exibição da forma de onda
      ↓ Envio via socket TCP
          ↕ rede local
[Host B — Receptor]
      ↑ Recepção via socket TCP
      ↑ Exibição da forma de onda
      ↑ Decodificação HDB3
      ↑ Binário → ASCII Estendido
      ↑ Descriptografia
  Mensagem reconstruída
```

---

## ✅ Requisitos atendidos

| Critério | Descrição | Pontuação |
|---|---|---|
| T1 | Interface gráfica com exibição de msg original, criptografada, binária, sinal HDB3 e gráfico | 1,0 pt |
| T2 | Forma de onda exibida no emissor (codificação) e no receptor (decodificação) | 2,0 pts |
| T3 | Comunicação entre dois ou mais computadores via rede local | 1,0 pt |
| T4 | Mecanismo de criptografia implementado e documentado | 1,5 pts |
| T5 | Conversão texto ↔ binário usando tabela ASCII Estendido (suporte a acentos) | 0,5 pt |
| T6 | Implementação completa do algoritmo HDB3 (encoder + decoder) | 2,0 pts |
| T7 | Envio da mensagem codificada para o outro computador via rede | 1,0 pt |
| T8 | Reconstrução completa da mensagem original no receptor | 1,0 pt |
| `*` | Ponto extra — algoritmo HDB3 | +0,25 pt |

---

## 🏗️ Estrutura do projeto

```
linecode-hdb3/
│
├── src/
│   ├── hdb3/
│   │   ├── __init__.py
│   │   ├── encoder.py          # Codificação HDB3
│   │   └── decoder.py          # Decodificação HDB3
│   │
│   ├── crypto/
│   │   ├── __init__.py
│   │   └── cipher.py           # Criptografia e descriptografia
│   │
│   ├── network/
│   │   ├── __init__.py
│   │   ├── sender.py           # Socket TCP — emissor
│   │   └── receiver.py         # Socket TCP — receptor
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py              # Janela principal (Tkinter)
│   │   ├── sender_panel.py     # Painel do emissor
│   │   ├── receiver_panel.py   # Painel do receptor
│   │   └── waveform.py         # Gráfico da forma de onda (matplotlib)
│   │
│   └── utils/
│       ├── __init__.py
│       └── ascii_converter.py  # Conversão texto ↔ binário (latin-1)
│
├── tests/
│   ├── test_hdb3.py
│   ├── test_crypto.py
│   └── test_ascii.py
│
├── docs/
│   └── criptografia.md         # Documentação do método de criptografia
│
├── requirements.txt
└── README.md
```

---

## 🔧 Tecnologias utilizadas

| Biblioteca | Uso | Instalação |
|---|---|---|
| `tkinter` | Interface gráfica | Já incluso no Python |
| `matplotlib` | Gráficos da forma de onda | `pip install matplotlib` |
| `socket` | Comunicação TCP em rede | Já incluso no Python |
| `cryptography` | Algoritmo de criptografia | `pip install cryptography` |

> **Nota:** o mecanismo de comunicação em rede é implementado diretamente com a biblioteca `socket` padrão do Python — nenhuma ferramenta externa de rede é utilizada.

---

## ⚙️ Instalação e execução

### Pré-requisitos

- Python 3.10 ou superior
- Dois computadores na mesma rede local (Wi-Fi ou cabo)

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/linecode-hdb3.git
cd linecode-hdb3
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Executar

**No computador receptor (Host B) — iniciar primeiro:**
```bash
python src/ui/app.py --mode receiver --port 5000
```

**No computador emissor (Host A):**
```bash
python src/ui/app.py --mode sender --host <IP_DO_RECEPTOR> --port 5000
```

> Para descobrir o IP do receptor, execute `ipconfig` (Windows) ou `ip a` (Linux/macOS).

---

## 📡 Como funciona o HDB3

O HDB3 (*High Density Bipolar 3*) é uma variação do AMI que resolve o problema de longos períodos de nível zero, os quais causam perda de sincronismo.

**Regra base:** grupos de **4 zeros consecutivos** são substituídos por sequências especiais com pulsos de violação (V) e bipolar (B):

| Pulsos não-zero desde a última substituição | Substituição aplicada |
|---|---|
| Ímpar | `000V` |
| Par | `B00V` |

Onde:
- **V** (violation): pulso com **mesma** polaridade do anterior — viola a regra AMI intencionalmente para ser detectado
- **B** (bipolar): pulso com polaridade normal AMI

**Exemplo:**

```
Bits originais:  1  0  0  0  0  1  0  0  0  0
AMI normal:     +1  0  0  0  0 -1  0  0  0  0
HDB3:           +1  0  0  0 +V -1  B  0  0 -V
                           ↑ 000V         ↑ B00V
```

A decodificação detecta os pulsos V (violação da alternância), descarta os B adjacentes e reconstrói os zeros originais.

---

## 🔐 Criptografia

O método de criptografia utilizado é documentado em [`docs/criptografia.md`](docs/criptografia.md).

---

## 👥 Equipe e divisão de tarefas

| Integrante | Responsabilidade |
|---|---|
| **[Nome A]** | Algoritmo HDB3 (encoder/decoder), conversão ASCII Estendido, criptografia |
| **[Nome B]** | Interface gráfica (Tkinter), gráficos da forma de onda (matplotlib), UX |
| **[Nome C]** | Comunicação em rede (sockets TCP), integração entre módulos, testes |

---

## 🧪 Testes

Para rodar os testes unitários:

```bash
python -m pytest tests/
```

Os testes cobrem especialmente o encoder/decoder HDB3 com as sequências de referência da aula, garantindo que a codificação e decodificação são simétricas.

---

## 📚 Referências

- FOROUZAN, B. A. *Comunicação de Dados e Redes de Computadores*. 4ª ed. McGraw-Hill, 2008. (Capítulo 4 — Transmissão Digital)
- Slides da disciplina: Prof. Hermes Irineu Del Monego — DAELN/UTFPR Curitiba
- Normas do trabalho — Codificação de Linha (2025)

---

<p align="center">
  UTFPR — Universidade Tecnológica Federal do Paraná · Câmpus Curitiba<br>
  Departamento Acadêmico de Eletrônica · Comunicação de Dados
</p>
