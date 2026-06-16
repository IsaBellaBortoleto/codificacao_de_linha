# ═══════════════════════════════════════════════════════════════
# HDB3 — Encoder
# ═══════════════════════════════════════════════════════════════

def encode_hdb3(bits: list[int]) -> list[int]:
    """
    Codifica lista de bits (0/1) para símbolos HDB3 (-1, 0, +1).

    Passo 1 — AMI:
        Cada bit 1 recebe polaridade alternada (+1, -1, +1...); bit 0 = 0.

    Passo 2 — Substituição HDB3:
        Grupos de 4 zeros consecutivos são substituídos por:
          000V  se pulsos não-zero desde última substituição = ímpar
          B00V  se pulsos não-zero desde última substituição = par

        V = mesma polaridade do último pulso não-zero  (viola AMI → marcador)
        B = polaridade oposta ao último pulso não-zero (segue AMI → equilíbrio DC)
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

    # Passo 2: substituição HDB3
    result = raw[:]
    last_pol         = +1  # polaridade do último pulso não-zero
    non_zero_since   =  0  # contador desde última substituição

    i = 0
    while i < len(result):
        # Detectar grupo de 4 zeros consecutivos
        if i + 3 < len(raw) and raw[i]==0 and raw[i+1]==0 and raw[i+2]==0 and raw[i+3]==0:
            V = last_pol  # violação = mesma polaridade do último

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
                last_pol       = B
                non_zero_since += 1  # B conta como pulso não-zero

            last_pol       = V
            non_zero_since = 0  # reset após substituição
            i += 4
        else:
            result[i] = raw[i]
            if raw[i] != 0:
                last_pol = raw[i]
                non_zero_since += 1
            i += 1

    return result


