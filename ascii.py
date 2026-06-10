# =============================================================================
# ascii_converter.py
# Conversão texto para binário usando ASCII Estendido e vice-versa
# Trabalho de Comunicação de Dados — Codificação de Linha HDB3
# UTFPR Curitiba — Prof. Hermes Irineu Del Monego
# =============================================================================


def texto_para_binario(texto: str) -> str:
    """
    Converte uma string de texto para uma string de bits (0s e 1s).

    Usa o encoding latin-1 (ISO 8859-1) implicitamente via ord(),
    que suporta caracteres acentuados como ã, ç, é, ó, etc.
    (ASCII Estendido — valores de 0 até 255).

    IMPORTANTE: só aceita caracteres com ord() <= 255.
    Caracteres Unicode fora desse range (ex: —, €, emojis)
    não são suportados e levantam um erro claro.

    Cada caractere vira exatamente 8 bits.

    Exemplo:
        texto_para_binario("AB") → "01000001_01000010"
        texto_para_binario("ã")  → "11100011"

    Parâmetros: mensagem a ser convertida

    Retorna: string contendo apenas '0' e '1'

    Levanta: 
        ValueError: se algum caractere não couber em 8 bits (ord > 255)
    """
    resultado = ""

    for char in texto:
        # ord() retorna o código numérico do caractere
        # Exemplo: ord('A') = 65 
        numero = ord(char)

        # ASCII Estendido só suporta valores de 0 a 255 (8 bits)
        # Caracteres Unicode como — (8212) ou € (8364) não são suportados
        if numero > 255:
            raise ValueError(
                f"Caractere '{char}' (ord={numero}) não é suportado pelo "
                f"ASCII Estendido (máx. 255). Use apenas letras, números, "
                f"acentos comuns (á é ã ç ü etc.) e símbolos básicos."
            )

        # bin() converte para binário com prefixo '0b'
        # [2:] remove o '0b'
        # .zfill(8) preenche com zeros à esquerda até 8 dígitos
        # Exemplo: bin(65) = '0b1000001' → [2:] = '1000001' → zfill(8) = '01000001'
        oito_bits = bin(numero)[2:].zfill(8)

        resultado += oito_bits

    return resultado


def binario_para_texto(binario: str) -> str:
    """
    Converte uma string de bits de volta para texto.
    Processo inverso de texto_para_binario().

    Agrupa os bits de 8 em 8, converte cada grupo para inteiro,
    depois para caractere usando chr().

    Exemplo:
        binario_para_texto("01000001") → "A"
        binario_para_texto("11100011") → "ã"

    Parâmetros:
        binario (str): string contendo apenas '0' e '1'
                       deve ter comprimento múltiplo de 8

    Retorna:
        str: texto reconstruído

    Levanta:
        ValueError: se o comprimento não for múltiplo de 8
    """
    if len(binario) % 8 != 0:
        raise ValueError(
            f"String de bits com comprimento {len(binario)} não é "
            f"múltiplo de 8. Cada caractere precisa de exatamente 8 bits."
        )

    resultado = ""

    # percorre de 8 em 8 posições — cada grupo é 1 byte = 1 caractere
    for i in range(0, len(binario), 8):
        grupo = binario[i:i+8]

        # int(grupo, 2) converte string binária para inteiro
        # Exemplo: int('01000001', 2) = 65
        numero = int(grupo, 2)

        # chr() converte o número de volta para caractere
        # Exemplo: chr(65) = 'A' | chr(227) = 'ã'
        resultado += chr(numero)

    return resultado


def validar_texto(texto: str) -> tuple[bool, str]:
    """
    Verifica se todos os caracteres do texto são suportados (ord <= 255).
    Útil para validar a entrada do usuário na interface antes de processar.

    Parâmetros:
        texto (str): texto a ser validado

    Retorna:
        tuple (bool, str):
            (True, "")           → texto válido
            (False, mensagem)    → texto inválido, mensagem explica o problema
    """
    for char in texto:
        if ord(char) > 255:
            return False, (
                f"O caractere '{char}' não é suportado. "
                f"Evite travessão (—), aspas curvas ("")  e emojis."
            )
    return True, ""


# -----------------------------------------------------------------------------
# TESTES
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("TESTES — ascii_converter.py")
    print("=" * 60)

    # --- Teste 1: casos válidos ---
    print("\n[1] Caracteres suportados")
    casos_validos = [
        "A",
        "Olá",
        "Batman",
        "ç à é ü ñ",
        "HDB3 UTFPR 2025!",
        "transmissao de dados",
    ]

    for texto in casos_validos:
        bits = texto_para_binario(texto)
        reconstruido = binario_para_texto(bits)
        status = "✓" if texto == reconstruido else "X"
        print(f"  {status} '{texto}'")
        print(f"     Bits ({len(bits)}): {bits[:32]}{'...' if len(bits) > 32 else ''}")
        print(f"     Reconstruído: '{reconstruido}'")

    # --- Teste 2: caracteres inválidos ---
    print("\n[2] Caracteres NÃO suportados (devem levantar erro)")
    casos_invalidos = ["—", "€", "🦇"]

    for char in casos_invalidos:
        try:
            texto_para_binario(char)
            print(f"  X '{char}' deveria ter levantado erro!")
        except ValueError as e:
            print(f"  ✓ '{char}' → ValueError capturado corretamente")

    # --- Teste 3: validar_texto ---
    print("\n[3] Função validar_texto()")
    valido, msg = validar_texto("Olá, tudo bem?")
    print(f"  ✓ Texto válido: {valido}")

    valido, msg = validar_texto("texto com travessão —")
    print(f"  ✓ Texto inválido detectado: {not valido} → {msg}")

    print("\n" + "=" * 60)