"""
Interface Gráfica - Codificação HDB3
Trabalho de Redes - Comunicação ESP32 via ESP-NOW

Dependências:
    pip install customtkinter pyserial matplotlib

Uso:
    python interface.py

Protocolo Serial:
    PC → Master  : JSON {"bits":"...", "key": N, "original": "texto"}
    Slave → PC   : JSON {"type":"received", "hdb3":[...], "bits":"...", "decoded":"..."}
"""

import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import serial
import serial.tools.list_ports
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as mpatches


# ═══════════════════════════════════════════════════════════════════
# HDB3 ENCODER (espelho do firmware – usado para preview local)
# ═══════════════════════════════════════════════════════════════════

def text_to_binary(text: str) -> str:
    """Converte texto para binário usando ASCII estendido (8 bits/char)."""
    return ''.join(format(ord(c), '08b') for c in text)

def xor_encrypt(text: str, key: int) -> str:
    """Criptografia XOR simples, revertível com a mesma chave."""
    return ''.join(chr(ord(c) ^ key) for c in text)

def xor_decrypt(text: str, key: int) -> str:
    return xor_encrypt(text, key)  # XOR é auto-inverso

def encode_hdb3(bits: list[int]) -> list[int]:
    """
    Codifica lista de bits (0/1) para símbolos HDB3 (-1, 0, +1).

    Regras HDB3:
      - Sequências de 4 zeros consecutivos são substituídas por:
          000V  se pulsos não-zero desde última substituição = ímpar
          B00V  se pulsos não-zero desde última substituição = par
      - V = violação (mesma polaridade do último pulso não-zero)
      - B = pulso bipolar normal (inverte polaridade = segue AMI)
    """
    # Passo 1: AMI raw
    raw = []
    polarity = +1
    for b in bits:
        if b == 0:
            raw.append(0)
        else:
            raw.append(polarity)
            polarity = -polarity

    # Passo 2: HDB3 – substituição de grupos de 4 zeros
    result = raw[:]
    last_pol = +1
    non_zero_since = 0
    i = 0
    while i < len(result):
        # Detectar grupo de 4 zeros
        if i + 3 < len(result) and all(raw[i+k] == 0 for k in range(4)):
            V = last_pol  # violação
            if non_zero_since % 2 == 1:
                # ímpar → 000V
                result[i]   = 0
                result[i+1] = 0
                result[i+2] = 0
                result[i+3] = V
            else:
                # par → B00V
                B = -last_pol
                result[i]   = B
                result[i+1] = 0
                result[i+2] = 0
                result[i+3] = V
                last_pol = B
                non_zero_since += 1
            last_pol = V
            non_zero_since = 0
            i += 4
        else:
            result[i] = raw[i]
            if raw[i] != 0:
                last_pol = raw[i]
                non_zero_since += 1
            i += 1

    return result

def decode_hdb3(hdb3: list[int]) -> list[int]:
    """
    Decodifica símbolos HDB3 de volta para bits (0/1).
    Remove substituições identificando violações AMI.
    """
    temp = hdb3[:]
    last_pol = 0

    for i in range(len(temp)):
        if temp[i] == 0:
            continue
        if last_pol != 0 and temp[i] == last_pol:
            # Violação detectada
            if i >= 3:
                if temp[i-1] == 0 and temp[i-2] == 0 and temp[i-3] == 0:
                    # 000V
                    temp[i] = 0
                elif temp[i-1] == 0 and temp[i-2] == 0 and temp[i-3] != 0:
                    # B00V
                    temp[i-3] = 0
                    temp[i]   = 0
        else:
            last_pol = temp[i]

    return [1 if s != 0 else 0 for s in temp]


# ═══════════════════════════════════════════════════════════════════
# COMUNICAÇÃO SERIAL
# ═══════════════════════════════════════════════════════════════════

class SerialManager:
    def __init__(self, callback_received):
        self.ser_master = None
        self.ser_slave  = None
        self.callback   = callback_received
        self._running   = False

    def list_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect_master(self, port, baud=115200):
        self.ser_master = serial.Serial(port, baud, timeout=1)

    def connect_slave(self, port, baud=115200):
        self.ser_slave = serial.Serial(port, baud, timeout=1)
        self._running = True
        t = threading.Thread(target=self._read_slave, daemon=True)
        t.start()

    def send_to_master(self, data: dict):
        if not self.ser_master or not self.ser_master.is_open:
            raise ConnectionError("Master não conectado")
        payload = (json.dumps(data) + '\n').encode()
        self.ser_master.write(payload)
        # Aguardar resposta
        time.sleep(0.6)
        if self.ser_master.in_waiting:
            line = self.ser_master.readline().decode(errors='ignore').strip()
            return json.loads(line) if line else {}
        return {}

    def _read_slave(self):
        while self._running and self.ser_slave and self.ser_slave.is_open:
            try:
                if self.ser_slave.in_waiting:
                    line = self.ser_slave.readline().decode(errors='ignore').strip()
                    if line:
                        data = json.loads(line)
                        self.callback(data)
            except Exception:
                pass
            time.sleep(0.05)

    def disconnect(self):
        self._running = False
        if self.ser_master: self.ser_master.close()
        if self.ser_slave:  self.ser_slave.close()


# ═══════════════════════════════════════════════════════════════════
# WIDGET DE GRÁFICO HDB3
# ═══════════════════════════════════════════════════════════════════

def draw_hdb3_waveform(ax, symbols: list[int], title: str, color_pos="#00d4aa",
                        color_neg="#ff6b6b", color_zero="#4a4a6a"):
    """Desenha forma de onda HDB3 com step plot e marcações de V e B."""
    ax.clear()
    ax.set_facecolor("#0d0d1a")

    if not symbols:
        ax.set_title(title, color="white", fontsize=10, pad=8)
        return

    # Construir coordenadas do sinal em degrau
    x, y = [], []
    for i, s in enumerate(symbols):
        x += [i, i+1]
        y += [s, s]

    # Segmentos coloridos
    for i in range(len(symbols)):
        c = color_pos if symbols[i] > 0 else (color_neg if symbols[i] < 0 else color_zero)
        ax.plot([i, i+1], [symbols[i], symbols[i]], color=c, linewidth=2.5, solid_capstyle='round')
        # Linha vertical de transição
        if i > 0 and symbols[i] != symbols[i-1]:
            ax.plot([i, i], [symbols[i-1], symbols[i]], color="#666688", linewidth=1, linestyle='--')

    # Linha de base
    ax.axhline(0, color="#333355", linewidth=0.8, linestyle=':')

    # Detectar violações para marcar no gráfico
    last_pol = 0
    for i, s in enumerate(symbols):
        if s == 0:
            continue
        if last_pol != 0 and s == last_pol:
            ax.annotate('V', xy=(i+0.5, s), fontsize=7, color='#ffcc00',
                        ha='center', va='bottom' if s > 0 else 'top',
                        fontweight='bold')
        last_pol = s

    ax.set_xlim(0, len(symbols))
    ax.set_ylim(-1.8, 1.8)
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(['-1', '0', '+1'], color='#aaaacc', fontsize=8)
    ax.tick_params(axis='x', colors='#aaaacc', labelsize=7)
    ax.set_title(title, color="#e0e0ff", fontsize=10, pad=8, fontweight='bold')
    ax.set_xlabel("Símbolos", color="#7777aa", fontsize=8)
    ax.spines['bottom'].set_color('#333355')
    ax.spines['left'].set_color('#333355')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Legenda
    patches = [
        mpatches.Patch(color=color_pos,  label='+1 (bipolar)'),
        mpatches.Patch(color=color_neg,  label='-1 (bipolar)'),
        mpatches.Patch(color=color_zero, label=' 0 (zero)'),
    ]
    ax.legend(handles=patches, loc='upper right', fontsize=6,
              facecolor='#1a1a2e', edgecolor='#333355', labelcolor='#ccccee')


# ═══════════════════════════════════════════════════════════════════
# INTERFACE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

PALETTE = {
    "bg":       "#0d0d1a",
    "panel":    "#12122a",
    "card":     "#1a1a35",
    "accent":   "#00d4aa",
    "accent2":  "#7c6aff",
    "danger":   "#ff6b6b",
    "text":     "#e0e0ff",
    "subtext":  "#7777aa",
    "border":   "#2a2a4a",
}

class HDB3App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HDB3 Line Coding — Comunicação ESP-NOW")
        self.geometry("1400x900")
        self.configure(fg_color=PALETTE["bg"])
        self.resizable(True, True)

        self.serial_mgr = SerialManager(self._on_slave_data)
        self._current_hdb3   = []
        self._received_hdb3  = []
        self._build_ui()

    # ── Construção da UI ───────────────────────────────────────────
    def _build_ui(self):
        # Título
        header = ctk.CTkFrame(self, fg_color=PALETTE["panel"], corner_radius=0, height=56)
        header.pack(fill="x", padx=0, pady=0)
        ctk.CTkLabel(header, text="⬡  HDB3 Line Coding",
                     font=("Courier New", 22, "bold"),
                     text_color=PALETTE["accent"]).pack(side="left", padx=24, pady=12)
        ctk.CTkLabel(header, text="ESP-NOW · 3× ESP32 · Python",
                     font=("Courier New", 11),
                     text_color=PALETTE["subtext"]).pack(side="right", padx=24)

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=8)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent, fg_color=PALETTE["panel"],
                            corner_radius=12, border_width=1,
                            border_color=PALETTE["border"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        left.columnconfigure(0, weight=1)

        # ── Seção: Conexão Serial ──────────────────────────────────
        self._section(left, "CONEXÃO SERIAL", 0)

        conn_frame = ctk.CTkFrame(left, fg_color=PALETTE["card"], corner_radius=8)
        conn_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,8))
        conn_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(conn_frame, text="Master COM:", text_color=PALETTE["subtext"],
                     font=("Courier New", 11)).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.combo_master = ctk.CTkComboBox(conn_frame, values=self.serial_mgr.list_ports(),
                                             fg_color=PALETTE["bg"], border_color=PALETTE["border"],
                                             button_color=PALETTE["accent2"],
                                             text_color=PALETTE["text"], width=120)
        self.combo_master.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        ctk.CTkLabel(conn_frame, text="Slave COM:", text_color=PALETTE["subtext"],
                     font=("Courier New", 11)).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self.combo_slave = ctk.CTkComboBox(conn_frame, values=self.serial_mgr.list_ports(),
                                            fg_color=PALETTE["bg"], border_color=PALETTE["border"],
                                            button_color=PALETTE["accent2"],
                                            text_color=PALETTE["text"], width=120)
        self.combo_slave.grid(row=1, column=1, padx=8, pady=6, sticky="ew")

        btn_conn = ctk.CTkButton(conn_frame, text="⚡ Conectar", command=self._connect_serial,
                                  fg_color=PALETTE["accent2"], hover_color="#5a4acc",
                                  text_color="white", font=("Courier New", 11, "bold"),
                                  corner_radius=6)
        btn_conn.grid(row=2, column=0, columnspan=2, padx=8, pady=(4,8), sticky="ew")

        self.lbl_conn_status = ctk.CTkLabel(conn_frame, text="● Desconectado",
                                             text_color=PALETTE["danger"],
                                             font=("Courier New", 10))
        self.lbl_conn_status.grid(row=3, column=0, columnspan=2, padx=8, pady=(0,6))

        # ── Seção: Mensagem ────────────────────────────────────────
        self._section(left, "HOST A — ENVIO", 2)

        msg_frame = ctk.CTkFrame(left, fg_color=PALETTE["card"], corner_radius=8)
        msg_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0,8))
        msg_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(msg_frame, text="Mensagem original:",
                     text_color=PALETTE["subtext"], font=("Courier New", 10)).grid(
                     row=0, column=0, padx=10, pady=(8,2), sticky="w")
        self.entry_msg = ctk.CTkEntry(msg_frame, placeholder_text="Digite sua mensagem...",
                                       fg_color=PALETTE["bg"], border_color=PALETTE["accent"],
                                       text_color=PALETTE["text"], font=("Courier New", 12),
                                       height=36)
        self.entry_msg.grid(row=1, column=0, padx=10, pady=(0,8), sticky="ew")

        ctk.CTkLabel(msg_frame, text="Chave XOR (0–255):",
                     text_color=PALETTE["subtext"], font=("Courier New", 10)).grid(
                     row=2, column=0, padx=10, pady=(0,2), sticky="w")
        self.entry_key = ctk.CTkEntry(msg_frame, placeholder_text="Ex: 42",
                                       fg_color=PALETTE["bg"], border_color=PALETTE["accent2"],
                                       text_color=PALETTE["text"], font=("Courier New", 12),
                                       width=100, height=32)
        self.entry_key.insert(0, "42")
        self.entry_key.grid(row=3, column=0, padx=10, pady=(0,8), sticky="w")

        btn_send = ctk.CTkButton(msg_frame, text="▶  Processar & Enviar",
                                  command=self._process_and_send,
                                  fg_color=PALETTE["accent"], hover_color="#00a882",
                                  text_color="#0d0d1a", font=("Courier New", 13, "bold"),
                                  corner_radius=6, height=40)
        btn_send.grid(row=4, column=0, padx=10, pady=(4,10), sticky="ew")

        # ── Seção: Campos de exibição (T1) ─────────────────────────
        self._section(left, "PIPELINE DE TRANSFORMAÇÃO (T1)", 4)

        fields_frame = ctk.CTkScrollableFrame(left, fg_color=PALETTE["card"],
                                               corner_radius=8, height=220)
        fields_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=(0,8))
        fields_frame.columnconfigure(0, weight=1)

        self.fields = {}
        labels = [
            ("msg_original",  "📝 Mensagem original:"),
            ("msg_cripto",    "🔐 Mensagem criptografada (XOR):"),
            ("msg_bin",       "⚙  Binário (ASCII ext.):"),
            ("msg_hdb3_str",  "📡 Símbolos HDB3:"),
        ]
        for i, (key, lbl) in enumerate(labels):
            ctk.CTkLabel(fields_frame, text=lbl, text_color=PALETTE["subtext"],
                         font=("Courier New", 9)).grid(row=i*2, column=0, padx=8, pady=(6,0), sticky="w")
            tb = ctk.CTkTextbox(fields_frame, height=36, fg_color=PALETTE["bg"],
                                text_color=PALETTE["accent"], font=("Courier New", 9),
                                border_color=PALETTE["border"], border_width=1, wrap="none")
            tb.grid(row=i*2+1, column=0, padx=8, pady=(0,4), sticky="ew")
            tb.configure(state="disabled")
            self.fields[key] = tb

        # ── Seção: Recepção (Host B) ───────────────────────────────
        self._section(left, "HOST B — RECEPÇÃO", 6)

        recv_frame = ctk.CTkScrollableFrame(left, fg_color=PALETTE["card"],
                                             corner_radius=8, height=140)
        recv_frame.grid(row=7, column=0, sticky="ew", padx=12, pady=(0,12))
        recv_frame.columnconfigure(0, weight=1)

        recv_labels = [
            ("recv_hdb3",    "📥 HDB3 recebido:"),
            ("recv_bits",    "⚙  Bits decodificados:"),
            ("recv_decoded", "✅ Mensagem recuperada:"),
        ]
        for i, (key, lbl) in enumerate(recv_labels):
            ctk.CTkLabel(recv_frame, text=lbl, text_color=PALETTE["subtext"],
                         font=("Courier New", 9)).grid(row=i*2, column=0, padx=8, pady=(6,0), sticky="w")
            tb = ctk.CTkTextbox(recv_frame, height=32, fg_color=PALETTE["bg"],
                                text_color=PALETTE["accent"], font=("Courier New", 9),
                                border_color=PALETTE["border"], border_width=1, wrap="none")
            tb.grid(row=i*2+1, column=0, padx=8, pady=(0,4), sticky="ew")
            tb.configure(state="disabled")
            self.fields[key] = tb

    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color=PALETTE["panel"],
                              corner_radius=12, border_width=1,
                              border_color=PALETTE["border"])
        right.grid(row=0, column=1, sticky="nsew", padx=(6,0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)

        self._section(right, "FORMA DE ONDA — HOST A (TRANSMISSÃO)", 0)
        fig_a = Figure(figsize=(6, 2.8), dpi=96, facecolor=PALETTE["bg"])
        self.ax_a = fig_a.add_subplot(111)
        self.ax_a.set_facecolor(PALETTE["bg"])
        fig_a.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.18)
        self.canvas_a = FigureCanvasTkAgg(fig_a, master=right)
        self.canvas_a.get_tk_widget().configure(bg=PALETTE["bg"], highlightthickness=0)
        self.canvas_a.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=12, pady=(0,8))

        self._section(right, "FORMA DE ONDA — HOST B (RECEPÇÃO)", 2)
        fig_b = Figure(figsize=(6, 2.8), dpi=96, facecolor=PALETTE["bg"])
        self.ax_b = fig_b.add_subplot(111)
        self.ax_b.set_facecolor(PALETTE["bg"])
        fig_b.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.18)
        self.canvas_b = FigureCanvasTkAgg(fig_b, master=right)
        self.canvas_b.get_tk_widget().configure(bg=PALETTE["bg"], highlightthickness=0)
        self.canvas_b.get_tk_widget().grid(row=3, column=0, sticky="nsew", padx=12, pady=(0,12))

        # Instrução placeholder
        draw_hdb3_waveform(self.ax_a, [], "Aguardando envio...")
        draw_hdb3_waveform(self.ax_b, [], "Aguardando recepção...")
        self.canvas_a.draw()
        self.canvas_b.draw()

    def _section(self, parent, text, row):
        fr = ctk.CTkFrame(parent, fg_color="transparent", height=28)
        fr.grid(row=row, column=0, sticky="ew", padx=12, pady=(10,2))
        ctk.CTkLabel(fr, text=f"  {text}",
                     font=("Courier New", 9, "bold"),
                     text_color=PALETTE["accent2"],
                     fg_color=PALETTE["border"],
                     corner_radius=4).pack(fill="x")

    # ── Lógica ─────────────────────────────────────────────────────
    def _connect_serial(self):
        try:
            port_m = self.combo_master.get()
            port_s = self.combo_slave.get()
            if port_m:
                self.serial_mgr.connect_master(port_m)
            if port_s and port_s != port_m:
                self.serial_mgr.connect_slave(port_s)
            self.lbl_conn_status.configure(text="● Conectado", text_color=PALETTE["accent"])
        except Exception as e:
            messagebox.showerror("Erro de conexão", str(e))

    def _process_and_send(self):
        msg = self.entry_msg.get().strip()
        if not msg:
            messagebox.showwarning("Atenção", "Digite uma mensagem.")
            return
        try:
            key = int(self.entry_key.get().strip()) & 0xFF
        except ValueError:
            messagebox.showerror("Erro", "Chave XOR deve ser um número inteiro 0–255.")
            return

        # T4 – Criptografia XOR
        encrypted = xor_encrypt(msg, key)

        # T5 – Binário ASCII estendido
        binary_str = text_to_binary(encrypted)
        bits = [int(b) for b in binary_str]

        # T6 – HDB3
        hdb3 = encode_hdb3(bits)
        self._current_hdb3 = hdb3
        hdb3_str = ','.join(str(s) for s in hdb3)

        # Atualizar campos (T1)
        self._set_field("msg_original",  msg)
        self._set_field("msg_cripto",    encrypted + f"  [key={key}]")
        self._set_field("msg_bin",       binary_str)
        self._set_field("msg_hdb3_str",  hdb3_str)

        # T2 – Gráfico Host A
        draw_hdb3_waveform(self.ax_a, hdb3, f"HDB3 — Host A (transmissão) | {len(hdb3)} símbolos")
        self.canvas_a.draw()

        # T3/T7 – Enviar para ESP32 Master via Serial
        payload = {
            "bits":     binary_str,
            "key":      key,
            "original": msg,
        }
        try:
            resp = self.serial_mgr.send_to_master(payload)
            if resp:
                status = f"Entregue a {resp.get('delivered',0)}/{resp.get('slaves',2)} slaves"
                self.lbl_conn_status.configure(text=f"● {status}", text_color=PALETTE["accent"])
        except ConnectionError:
            # Modo demo: simular recepção localmente
            self._simulate_reception(hdb3, key)

    def _simulate_reception(self, hdb3: list[int], key: int):
        """Simulação local quando ESP32 não está conectado (demo)."""
        bits_decoded = decode_hdb3(hdb3)
        bits_str = ''.join(str(b) for b in bits_decoded)

        # Reconstruir texto
        chars = []
        for i in range(0, len(bits_decoded)-7, 8):
            byte_val = int(bits_str[i:i+8], 2)
            chars.append(chr(byte_val ^ key))
        decoded_msg = ''.join(chars)

        data = {
            "type":    "received",
            "hdb3":    hdb3,
            "bits":    bits_str,
            "decoded": decoded_msg,
            "key":     key,
        }
        self._on_slave_data(data)

    def _on_slave_data(self, data: dict):
        """Callback quando Slave envia dados ao PC (T8)."""
        if data.get("type") != "received":
            return

        hdb3 = data.get("hdb3", [])
        if isinstance(hdb3, str):
            import ast
            hdb3 = ast.literal_eval(hdb3)

        bits_str  = data.get("bits", "")
        decoded   = data.get("decoded", "")

        self._set_field("recv_hdb3",    ','.join(str(s) for s in hdb3[:80]) + ("..." if len(hdb3) > 80 else ""))
        self._set_field("recv_bits",    bits_str[:128] + ("..." if len(bits_str) > 128 else ""))
        self._set_field("recv_decoded", decoded)

        # T2 – Gráfico Host B
        self.after(0, lambda: self._update_recv_graph(hdb3))

    def _update_recv_graph(self, hdb3):
        draw_hdb3_waveform(self.ax_b, hdb3, f"HDB3 — Host B (recepção/decodificação) | {len(hdb3)} símbolos")
        self.canvas_b.draw()

    def _set_field(self, key: str, value: str):
        tb = self.fields.get(key)
        if tb:
            tb.configure(state="normal")
            tb.delete("1.0", "end")
            tb.insert("1.0", value)
            tb.configure(state="disabled")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = HDB3App()
    app.mainloop()
