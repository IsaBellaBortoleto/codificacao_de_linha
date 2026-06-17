# =============================================================================
# crypto.py
# Módulo de criptografia XOR com chave 
# Trabalho de Comunicação de Dados — Codificação de Linha HDB3
# UTFPR Curitiba — Prof. Hermes Irineu Del Monego
# =============================================================================

from ascii import texto_para_binario, binario_para_texto, validar_texto

# -----------------------------------------------------------------------------
# Chave de criptografia XOR
# "internet explorer" em ASCII — 17 bytes
# Em binário:
#   01101001 01101110 01110100 01100101 01110010 01101110 01100101 01110100
#   00100000 01100101 01111000 01110000 01101100 01101111 01110010 01100101
#   01110010
# -----------------------------------------------------------------------------
CHAVE = "internet explorer"


# -----------------------------------------------------------------------------
# CRIPTOGRAFIA XOR
# -----------------------------------------------------------------------------

def criptografar(texto: str, chave: str = CHAVE) -> str:
    """
    Criptografa um texto usando XOR bit a bit com uma chave cíclica.

    O XOR (ou exclusivo) funciona assim:
        0 XOR 0 = 0
        0 XOR 1 = 1
        1 XOR 0 = 1
        1 XOR 1 = 0

    Propriedade fundamental:
        mensagem XOR chave = cifrado
        cifrado  XOR chave = mensagem  ← XOR é seu próprio inverso!

    A chave se repete ciclicamente com o operador módulo (%):
        índice_chave = i % len(chave)
    Isso garante que a chave nunca acaba, independente do tamanho da mensagem.

    Parâmetros:
        texto (str): mensagem a ser criptografada
        chave (str): chave XOR — padrão: "internet explorer"

    Retorna:
        str: texto criptografado
    """
    resultado = ""

    for i, char in enumerate(texto):
        # pega o caractere da chave de forma cíclica
        # enumerate() fornece (índice, caractere) a cada iteração
        char_chave = chave[i % len(chave)]

        # XOR entre os códigos numéricos dos dois caracteres
        # ^ é o operador XOR em Python
        codigo_xor = ord(char) ^ ord(char_chave)

        # converte o resultado de volta para caractere
        resultado += chr(codigo_xor)

    return resultado


def descriptografar(texto_cifrado: str, chave: str = CHAVE) -> str:
    """
    Descriptografa um texto criptografado com XOR.

    Como XOR é seu próprio inverso, a operação de descriptografia
    é matematicamente idêntica à criptografia:
        cifrado XOR chave = mensagem original

    Parâmetros:
        texto_cifrado (str): texto criptografado
        chave (str): mesma chave usada na criptografia

    Retorna:
        str: mensagem original reconstruída
    """
    # a operação é exatamente a mesma — XOR é simétrico
    return criptografar(texto_cifrado, chave)


# -----------------------------------------------------------------------------
# PIPELINE — funções de alto nível chamadas pela UI
# -----------------------------------------------------------------------------

def processar_envio(mensagem: str) -> dict:
    """
    Pipeline completo do emissor (Host A):
        1. Valida o texto (apenas ASCII Estendido — ord <= 255)
        2. Criptografia XOR
        3. Conversão para binário (ASCII Estendido)

    A string de binário retornada é a entrada para o encoder HDB3.

    Parâmetros:
        mensagem (str): texto digitado pelo usuário na interface

    Retorna:
        dict com:
            'original'      → texto original
            'criptografado' → texto após XOR
            'binario'       → string de bits para o HDB3
            'erro'          → None se OK, string com mensagem se erro

    """
    # valida antes de processar
    valido, msg_erro = validar_texto(mensagem)
    if not valido:
        return {
            "original":      mensagem,
            "criptografado": "",
            "binario":       "",
            "erro":          msg_erro
        }

    texto_cifrado = criptografar(mensagem)
    bits = texto_para_binario(texto_cifrado)

    return {
        "original":      mensagem,
        "criptografado": texto_cifrado,
        "binario":       bits,
        "erro":          None
    }


def processar_recepcao(binario: str) -> dict:
    """
    Pipeline completo do receptor (Host B):
        1. Binário recebido (após decodificação HDB3)
        2. Conversão binário → texto criptografado
        3. Descriptografia XOR
        4. Mensagem original reconstruída

    Parâmetros:
        binario (str): string de bits após decodificação HDB3

    Retorna:
        dict com:
            'binario'       → string de bits recebida
            'criptografado' → texto antes da descriptografia
            'original'      → mensagem reconstruída
            'erro'          → None se OK, string com mensagem se erro
    """
    try:
        texto_cifrado = binario_para_texto(binario)
        mensagem = descriptografar(texto_cifrado)

        return {
            "binario":       binario,
            "criptografado": texto_cifrado,
            "original":      mensagem,
            "erro":          None
        }
    except ValueError as e:
        return {
            "binario":       binario,
            "criptografado": "",
            "original":      "",
            "erro":          str(e)
        }


# -----------------------------------------------------------------------------
# TESTES
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("TESTES — crypto.py")
    print("=" * 60)

    # --- Teste 1: XOR simétrico ---
    print("\n[1] Simetria do XOR")
    msg = "Batman"
    cifrado = criptografar(msg)
    decifrado = descriptografar(cifrado)
    status = "✓" if msg == decifrado else "X"
    print(f"  {status} Original:     '{msg}'")
    print(f"     Criptografado: {[ord(c) for c in cifrado]}")
    print(f"     Decifrado:    '{decifrado}'")

    # --- Teste 2: chave cíclica ---
    print("\n[2] Chave cíclica (mensagem maior que a chave)")
    msg_longa = "E" * 50  # 50 chars, chave tem 17
    cifrado_longo = criptografar(msg_longa)
    decifrado_longo = descriptografar(cifrado_longo)
    status = "✓" if msg_longa == decifrado_longo else "X"
    print(f"  {status} Mensagem de 50 chars com chave de 17 chars")

    # --- Teste 3: suporte a acentos ---
    print("\n[3] Suporte a caracteres especiais (ASCII Estendido)")
    msg_acentos = "transmissao com acento:á Ê í ó ú ç"
    cifrado_acentos = criptografar(msg_acentos)
    decifrado_acentos = descriptografar(cifrado_acentos)
    status = "✓" if msg_acentos == decifrado_acentos else "X"
    print(f"  {status} '{msg_acentos}'")
    print(f"     → '{decifrado_acentos}'")

    # --- Teste 4: pipeline completo ---
    print("\n[4] Pipeline completo emissor -> receptor")
    msg_pipeline = "HDB3 UTFPR Curitiba 2025!"
    envio = processar_envio(msg_pipeline)
    recepcao = processar_recepcao(envio["binario"])
    status = "✓" if msg_pipeline == recepcao["original"] else "X"
    print(f"  {status} Enviado:   '{envio['original']}'")
    print(f"     Binario:    {envio['binario'][:32]}...")
    print(f"     Recebido:  '{recepcao['original']}'")

    # --- Teste 5: caractere inválido ---
    print("\n[5] Rejeição de caractere inválido (Unicode fora do ASCII Estendido)")
    envio_invalido = processar_envio("texto com travessao unicode")
    status = "✓" if envio_invalido["erro"] is None else "✓ (sem erro como esperado)"
    print(f"  {status} Texto sem caracteres especiais: OK")

    envio_invalido2 = processar_envio("texto com — travessao")
    status = "✓" if envio_invalido2["erro"] is not None else "X"
    print(f"  {status} Texto com travessao (—) rejeitado: {envio_invalido2['erro']}")

    print("\n" + "=" * 60)