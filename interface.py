import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from pipeline import (
    abrir_serial,
    enviar_emissao_serial,
    fechar_serial,
    interpretar_payload_recebido,
    ler_payload_serial,
    listar_portas_seriais,
    processar_emissao,
)


class InterfaceHDB3(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Comunicacao de Dados - HDB3")
        self.geometry("1280x860")
        self.minsize(1100, 760)

        self.resultado_emissao = None
        self.serial_recepcao = None
        self.recebendo = False

        self._criar_widgets()

    def _criar_widgets(self):
        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=10, pady=10)

        self.aba_emissao = ttk.Frame(abas)
        self.aba_recepcao = ttk.Frame(abas)

        abas.add(self.aba_emissao, text="Emissao")
        abas.add(self.aba_recepcao, text="Recepcao")

        self._criar_aba_emissao()
        self._criar_aba_recepcao()

    def _criar_aba_emissao(self):
        topo = ttk.LabelFrame(self.aba_emissao, text="Dados para transmitir", padding=10)
        topo.pack(fill="x", padx=5, pady=5)

        ttk.Label(topo, text="Texto original:").grid(row=0, column=0, sticky="w")
        self.texto_entry = ttk.Entry(topo)
        self.texto_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(topo, text="Chave XOR:").grid(row=0, column=1, sticky="w")
        self.chave_entry = ttk.Entry(topo, width=20)
        self.chave_entry.insert(0, "internet explorer")
        self.chave_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(topo, text="Usar slave:").grid(row=0, column=2, sticky="w")
        self.slave_selecionada = tk.StringVar(value="Slave 1")
        self.slave_combo = ttk.Combobox(
            topo,
            values=["Slave 1", "Slave 2"],
            textvariable=self.slave_selecionada,
            state="readonly",
            width=10,
        )
        self.slave_combo.grid(row=1, column=2, sticky="ew", padx=(0, 10))

        ttk.Label(topo, text="Porta Slave 1:").grid(row=0, column=3, sticky="w")
        self.porta_slave_1_combo = ttk.Combobox(topo, values=self._listar_portas(), width=18)
        self.porta_slave_1_combo.grid(row=1, column=3, sticky="ew", padx=(0, 10))

        ttk.Label(topo, text="Porta Slave 2:").grid(row=0, column=4, sticky="w")
        self.porta_slave_2_combo = ttk.Combobox(topo, values=self._listar_portas(), width=18)
        self.porta_slave_2_combo.grid(row=1, column=4, sticky="ew", padx=(0, 10))

        ttk.Button(topo, text="Atualizar portas", command=self._atualizar_portas).grid(
            row=1, column=5, padx=(0, 10)
        )
        ttk.Button(topo, text="Processar", command=self._processar_emissao).grid(
            row=1, column=6, padx=(0, 10)
        )
        ttk.Button(topo, text="Enviar para ESP", command=self._enviar_para_esp).grid(
            row=1, column=7
        )

        topo.columnconfigure(0, weight=1)

        saida = ttk.Notebook(self.aba_emissao)
        saida.pack(fill="both", expand=True, padx=5, pady=5)

        aba_textos = ttk.Frame(saida, padding=10)
        aba_binarios = ttk.Frame(saida, padding=10)
        aba_hdb3 = ttk.Frame(saida, padding=10)

        saida.add(aba_textos, text="Texto")
        saida.add(aba_binarios, text="Binarios")
        saida.add(aba_hdb3, text="HDB3")

        for aba in (aba_textos, aba_binarios, aba_hdb3):
            aba.columnconfigure(0, weight=1)
            aba.columnconfigure(1, weight=1)
            aba.rowconfigure(1, weight=1)
            aba.rowconfigure(3, weight=1)

        self.campos_emissao = {}
        self._criar_campo_saida(aba_textos, self.campos_emissao, "Texto original", "texto_original", 0, 0)
        self._criar_campo_saida(aba_textos, self.campos_emissao, "Texto criptografado", "texto_criptografado", 0, 1)
        self._criar_campo_saida(aba_binarios, self.campos_emissao, "Binario original", "binario_original", 0, 0)
        self._criar_campo_saida(aba_binarios, self.campos_emissao, "Binario criptografado", "binario", 0, 1)
        self._criar_campo_saida(aba_hdb3, self.campos_emissao, "Sinal HDB3", "sinal_hdb3", 0, 0)

        self.status_envio = tk.StringVar(value="Pronto.")
        ttk.Label(self.aba_emissao, textvariable=self.status_envio).pack(fill="x", padx=8)

        self.figura_envio, self.eixo_envio, self.canvas_envio = self._criar_grafico(self.aba_emissao)
        self._plotar_hdb3(self.eixo_envio, self.canvas_envio, [], "Sinal HDB3 - emissao")

    def _criar_aba_recepcao(self):
        topo = ttk.LabelFrame(self.aba_recepcao, text="Receber da ESP master", padding=10)
        topo.pack(fill="x", padx=5, pady=5)

        ttk.Label(topo, text="Porta ESP master:").grid(row=0, column=0, sticky="w")
        self.porta_recepcao_combo = ttk.Combobox(topo, values=self._listar_portas(), width=20)
        self.porta_recepcao_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(topo, text="Chave XOR:").grid(row=0, column=1, sticky="w")
        self.chave_recepcao_entry = ttk.Entry(topo, width=20)
        self.chave_recepcao_entry.insert(0, "internet explorer")
        self.chave_recepcao_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ttk.Button(topo, text="Atualizar portas", command=self._atualizar_portas).grid(
            row=1, column=2, padx=(0, 10)
        )
        ttk.Button(topo, text="Iniciar recepcao", command=self._iniciar_recepcao).grid(
            row=1, column=3, padx=(0, 10)
        )
        ttk.Button(topo, text="Parar", command=self._parar_recepcao).grid(row=1, column=4)

        topo.columnconfigure(0, weight=1)
        topo.columnconfigure(1, weight=1)

        saida = ttk.LabelFrame(self.aba_recepcao, text="Dados recebidos", padding=10)
        saida.pack(fill="both", expand=True, padx=5, pady=5)
        saida.columnconfigure(0, weight=1)
        saida.columnconfigure(1, weight=1)
        saida.rowconfigure(1, weight=1)
        saida.rowconfigure(3, weight=1)

        self.campos_recepcao = {}
        self._criar_campo_saida(saida, self.campos_recepcao, "HDB3 recebido", "sinal_hdb3", 0, 0)
        self._criar_campo_saida(saida, self.campos_recepcao, "Bits decodificados", "binario", 0, 1)
        self._criar_campo_saida(saida, self.campos_recepcao, "Texto criptografado", "texto_criptografado", 2, 0)
        self._criar_campo_saida(saida, self.campos_recepcao, "Texto original", "texto_original", 2, 1)

        self.status_recepcao = tk.StringVar(value="Recepcao parada.")
        ttk.Label(self.aba_recepcao, textvariable=self.status_recepcao).pack(fill="x", padx=8)

        self.figura_recepcao, self.eixo_recepcao, self.canvas_recepcao = self._criar_grafico(self.aba_recepcao)
        self._plotar_hdb3(self.eixo_recepcao, self.canvas_recepcao, [], "Sinal HDB3 - recepcao")

    def _criar_campo_saida(self, parent, colecao, titulo, chave, linha, coluna):
        ttk.Label(parent, text=titulo + ":").grid(row=linha, column=coluna, sticky="w")

        campo = ScrolledText(parent, height=4, wrap="word")
        campo.grid(row=linha + 1, column=coluna, sticky="nsew", padx=5, pady=(0, 8))
        campo.configure(state="disabled")

        colecao[chave] = campo

    def _criar_grafico(self, parent):
        frame = ttk.Frame(parent, padding=8)
        frame.pack(fill="both", expand=True)

        figura = Figure(figsize=(10, 3.4), dpi=100, constrained_layout=True)
        eixo = figura.add_subplot(111)
        canvas = FigureCanvasTkAgg(figura, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)

        return figura, eixo, canvas

    def _processar_emissao(self):
        texto = self.texto_entry.get()

        if not texto:
            messagebox.showwarning("Atencao", "Digite o texto original.")
            return

        try:
            resultado = processar_emissao(texto, self._ler_chave_bytes(self.chave_entry))
        except Exception as erro:
            messagebox.showerror("Erro no processamento", str(erro))
            return

        self.resultado_emissao = resultado
        self._mostrar_emissao(resultado)
        self.status_envio.set("Mensagem processada. Confira os campos e o grafico.")

    def _mostrar_emissao(self, resultado):
        self._preencher_campo(self.campos_emissao, "texto_original", resultado["texto_original"])
        self._preencher_campo(self.campos_emissao, "texto_criptografado", resultado["texto_criptografado"])
        self._preencher_campo(self.campos_emissao, "binario_original", resultado["binario_original"])
        self._preencher_campo(self.campos_emissao, "binario", resultado["binario"])
        self._preencher_campo(
            self.campos_emissao,
            "sinal_hdb3",
            self._lista_para_texto(resultado["sinal_hdb3"]),
        )
        self._plotar_hdb3(
            self.eixo_envio,
            self.canvas_envio,
            resultado["sinal_hdb3"],
            "Sinal HDB3 - emissao",
        )

    def _enviar_para_esp(self):
        if self.resultado_emissao is None:
            self._processar_emissao()
            if self.resultado_emissao is None:
                return

        porta = self._porta_slave_selecionada()
        if not porta:
            messagebox.showwarning("Atencao", "Selecione a porta serial da slave escolhida.")
            return

        try:
            resposta = enviar_emissao_serial(porta, self.resultado_emissao)
            if resposta.get("status") == "sem_resposta":
                self.status_envio.set(
                    f"Enviado pela {self.slave_selecionada.get()}, mas sem resposta."
                )
            else:
                self.status_envio.set(
                    f"Resposta da {self.slave_selecionada.get()}: " + str(resposta)
                )
        except Exception as erro:
            messagebox.showerror("Erro no envio serial", str(erro))

    def _iniciar_recepcao(self):
        porta = self.porta_recepcao_combo.get().strip()
        if not porta:
            messagebox.showwarning("Atencao", "Selecione a porta serial da ESP master.")
            return

        try:
            self._ler_chave_bytes(self.chave_recepcao_entry)
        except Exception as erro:
            messagebox.showerror("Erro na chave", str(erro))
            return

        if self.recebendo:
            return

        try:
            self.serial_recepcao = abrir_serial(porta)
        except Exception as erro:
            messagebox.showerror("Erro na recepcao serial", str(erro))
            return

        self.recebendo = True
        self.status_recepcao.set("Aguardando dados da ESP master...")

        thread = threading.Thread(target=self._loop_recepcao, daemon=True)
        thread.start()

    def _parar_recepcao(self):
        self.recebendo = False
        fechar_serial(self.serial_recepcao)

        self.serial_recepcao = None
        self.status_recepcao.set("Recepcao parada.")

    def _loop_recepcao(self):
        while self.recebendo and self.serial_recepcao and self.serial_recepcao.is_open:
            try:
                payload = ler_payload_serial(self.serial_recepcao)
                if payload:
                    self.after(0, self._tratar_payload_recebido, payload)
            except Exception as erro:
                self.after(0, self.status_recepcao.set, "Erro lendo serial: " + str(erro))
                break

    def _tratar_payload_recebido(self, payload):
        if payload.get("type") != "received" and "payload" not in payload:
            self.status_recepcao.set("Mensagem da ESP: " + str(payload))
            return

        try:
            chave = self._ler_chave_bytes(self.chave_recepcao_entry)
            resultado = interpretar_payload_recebido(payload, chave)
        except Exception as erro:
            messagebox.showerror("Erro ao processar recepcao", str(erro))
            return

        self._mostrar_recepcao(resultado)
        self.status_recepcao.set("Mensagem recebida de uma ESP slave via master.")

    def _mostrar_recepcao(self, resultado):
        self._preencher_campo(
            self.campos_recepcao,
            "sinal_hdb3",
            self._lista_para_texto(resultado.get("sinal_hdb3", [])),
        )
        self._preencher_campo(self.campos_recepcao, "binario", resultado.get("binario", ""))
        self._preencher_campo(
            self.campos_recepcao,
            "texto_criptografado",
            resultado.get("texto_criptografado", ""),
        )
        self._preencher_campo(
            self.campos_recepcao,
            "texto_original",
            resultado.get("texto_original", ""),
        )
        self._plotar_hdb3(
            self.eixo_recepcao,
            self.canvas_recepcao,
            resultado.get("sinal_hdb3", []),
            "Sinal HDB3 - recepcao",
        )

    def _ler_chave_bytes(self, campo):
        chave = campo.get()
        if not chave:
            raise ValueError("Digite a chave XOR.")

        return chave.encode("latin-1")

    def _listar_portas(self):
        return listar_portas_seriais()

    def _atualizar_portas(self):
        portas = self._listar_portas()
        self.porta_slave_1_combo.configure(values=portas)
        self.porta_slave_2_combo.configure(values=portas)
        self.porta_recepcao_combo.configure(values=portas)

    def _porta_slave_selecionada(self):
        if self.slave_selecionada.get() == "Slave 1":
            return self.porta_slave_1_combo.get().strip()

        return self.porta_slave_2_combo.get().strip()

    def _preencher_campo(self, colecao, chave, valor):
        campo = colecao[chave]
        campo.configure(state="normal")
        campo.delete("1.0", "end")
        campo.insert("1.0", str(valor))
        campo.configure(state="disabled")

    def _plotar_hdb3(self, eixo, canvas, sinal_hdb3, titulo):
        eixo.clear()
        eixo.set_title(titulo)
        eixo.set_xlabel("Tempo")
        eixo.set_ylabel("Nivel")
        eixo.set_ylim(-1.5, 1.5)
        eixo.set_yticks([-1, 0, 1])
        eixo.grid(True, linestyle="--", alpha=0.4)
        eixo.margins(x=0.01)

        if sinal_hdb3:
            x = []
            y = []
            for indice, nivel in enumerate(sinal_hdb3):
                x.extend([indice, indice + 1])
                y.extend([nivel, nivel])

            eixo.plot(x, y, drawstyle="steps-post")
            eixo.set_xlim(0, len(sinal_hdb3))
        else:
            eixo.set_xlim(0, 1)

        canvas.figure.tight_layout(pad=1.2)
        canvas.draw()

    def _lista_para_texto(self, valores):
        return ", ".join(str(valor) for valor in valores)


if __name__ == "__main__":
    app = InterfaceHDB3()
    app.mainloop()
