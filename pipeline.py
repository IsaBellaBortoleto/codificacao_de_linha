"""
Este modulo nao implementa ASCII, XOR ou HDB3. Ele apenas chama as
funcoes existentes e devolve os valores intermediarios para exibicao.
"""

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


def _chave_para_texto(chave: bytes) -> str:
    if not chave:
        raise ValueError("A chave XOR nao pode ser vazia.")

    return chave.decode("latin-1")


def _binario_para_lista_bits(binario: str) -> list[int]:
    return [int(bit) for bit in binario]


def _lista_bits_para_binario(bits: list[int]) -> str:
    return "".join(str(bit) for bit in bits)


def processar_emissao(texto: str, chave: bytes) -> dict:
    """
    Executa o fluxo do emissor:
    texto -> XOR -> binario ASCII estendido -> HDB3.
    """
    chave_texto = _chave_para_texto(chave)

    texto_criptografado = criptografar(texto, chave_texto)
    binario = texto_para_binario(texto_criptografado)
    bits = _binario_para_lista_bits(binario)
    sinal_hdb3 = encode_hdb3(bits)

    return {
        "texto_original": texto,
        "chave": chave,
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
