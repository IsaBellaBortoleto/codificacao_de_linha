"""
Pipeline entre a GUI, os algoritmos e as ESP32.

Este modulo nao implementa ASCII, XOR ou HDB3. Ele chama as funcoes
existentes, monta os valores intermediarios para exibicao e prepara os
payloads seriais usados pelos arquivos .ino.
"""

import ast
import json

try:
    from src.utils.ascii_converter import binario_para_texto, texto_para_binario
except ImportError:
    from ascii import binario_para_texto, texto_para_binario

try:
    from src.crypto.cipher import criptografar, descriptografar
except ImportError:
    from crypto import criptografar, descriptografar

try:
    from src.hdb3.encoder import encode_hdb3
    from src.hdb3.decoder import decode_hdb3
except ImportError:
    from encode import encode_hdb3
    from decode import decode_hdb3

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None


BAUD_RATE = 115200
MAX_SIMBOLOS_HDB3 = 200


def _chave_para_texto(chave: bytes) -> str:
    if not chave:
        raise ValueError("A chave XOR nao pode ser vazia.")

    return chave.decode("latin-1")


def _binario_para_lista_bits(binario: str) -> list[int]:
    return [int(bit) for bit in binario]


def _lista_bits_para_binario(bits: list[int]) -> str:
    return "".join(str(bit) for bit in bits)


def _normalizar_hdb3(valor) -> list[int]:
    if isinstance(valor, str):
        if all(simbolo in "+-0" for simbolo in valor):
            mapa = {"+": 1, "-": -1, "0": 0}
            return [mapa[simbolo] for simbolo in valor]

        valor = ast.literal_eval(valor)

    return [int(simbolo) for simbolo in valor]


def _hdb3_para_texto(sinal_hdb3: list[int]) -> str:
    mapa = {1: "+", -1: "-", 0: "0"}
    return "".join(mapa[int(simbolo)] for simbolo in sinal_hdb3)


def processar_emissao(texto: str, chave: bytes) -> dict:
    """
    Executa o fluxo do emissor:
    texto -> XOR -> binario ASCII estendido -> HDB3.
    """
    chave_texto = _chave_para_texto(chave)

    binario_original = texto_para_binario(texto)
    texto_criptografado = criptografar(texto, chave_texto)
    binario = texto_para_binario(texto_criptografado)
    bits = _binario_para_lista_bits(binario)
    sinal_hdb3 = encode_hdb3(bits)

    if len(sinal_hdb3) > MAX_SIMBOLOS_HDB3:
        raise ValueError(
            f"Sinal HDB3 com {len(sinal_hdb3)} simbolos. "
            f"O limite para envio ESP-NOW neste exemplo e {MAX_SIMBOLOS_HDB3}."
        )

    return {
        "texto_original": texto,
        "chave": chave,
        "binario_original": binario_original,
        "texto_criptografado": texto_criptografado,
        "binario": binario,
        "bits": bits,
        "sinal_hdb3": sinal_hdb3,
        "erro": None,
    }


def processar_recepcao(sinal_hdb3, chave: bytes) -> dict:
    """
    Executa o fluxo do receptor:
    HDB3 -> binario ASCII estendido -> texto criptografado -> XOR.
    """
    chave_texto = _chave_para_texto(chave)

    sinal_hdb3 = _normalizar_hdb3(sinal_hdb3)
    bits_decodificados = decode_hdb3(sinal_hdb3)
    binario = _lista_bits_para_binario(bits_decodificados)
    texto_criptografado = binario_para_texto(binario)
    texto_original = descriptografar(texto_criptografado, chave_texto)

    return {
        "sinal_hdb3": sinal_hdb3,
        "chave": chave,
        "bits_decodificados": bits_decodificados,
        "binario": binario,
        "texto_criptografado": texto_criptografado,
        "texto_original": texto_original,
        "erro": None,
    }


def montar_payload_envio(resultado_emissao: dict) -> dict:
    sinal_hdb3 = _normalizar_hdb3(resultado_emissao["sinal_hdb3"])

    if len(sinal_hdb3) > MAX_SIMBOLOS_HDB3:
        raise ValueError(
            f"Sinal HDB3 com {len(sinal_hdb3)} simbolos. "
            f"O limite para envio ESP-NOW neste exemplo e {MAX_SIMBOLOS_HDB3}."
        )

    return {
        "type": "send",
        "hdb3": _hdb3_para_texto(sinal_hdb3),
        "len": len(sinal_hdb3),
    }


def interpretar_payload_recebido(payload: dict, chave: bytes) -> dict:
    if "payload" in payload:
        payload = json.loads(payload["payload"])

    if payload.get("type") == "send":
        payload["type"] = "received"

    if payload.get("type") != "received":
        raise ValueError("Payload recebido nao e do tipo 'received'.")

    sinal_hdb3 = _normalizar_hdb3(payload.get("hdb3", []))
    return processar_recepcao(sinal_hdb3, chave)


def listar_portas_seriais() -> list[str]:
    if serial is None:
        return []

    return [porta.device for porta in serial.tools.list_ports.comports()]


def abrir_serial(porta: str, baud: int = BAUD_RATE):
    if serial is None:
        raise RuntimeError("PySerial nao esta instalado. Use: pip install pyserial")

    return serial.Serial(porta, baud, timeout=1)


def fechar_serial(conexao) -> None:
    if conexao and conexao.is_open:
        conexao.close()


def enviar_emissao_serial(porta: str, resultado_emissao: dict, baud: int = BAUD_RATE) -> dict:
    payload = montar_payload_envio(resultado_emissao)

    with abrir_serial(porta, baud) as conexao:
        conexao.timeout = 2
        linha_envio = json.dumps(payload, separators=(",", ":")) + "\n"
        conexao.write(linha_envio.encode("utf-8"))
        linha = conexao.readline().decode("utf-8", errors="ignore").strip()

    if not linha:
        return {"status": "sem_resposta"}

    return json.loads(linha)


def ler_payload_serial(conexao) -> dict | None:
    linha = conexao.readline().decode("utf-8", errors="ignore").strip()
    if not linha:
        return None

    return json.loads(linha)
