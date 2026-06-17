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
    result = []
    last_pol = -1
    non_zero_since = 0

    i = 0
    while i < len(bits):
        if bits[i] == 1:
            pulso = -last_pol
            result.append(pulso)
            last_pol = pulso
            non_zero_since += 1
            i += 1
            continue

        if i + 3 < len(bits) and bits[i:i+4] == [0, 0, 0, 0]:
            # Substituição HDB3 de quatro zeros consecutivos.
            # Se precisar de B, o V tem a mesma polaridade de B para
            # formar a violação detectável no receptor.
            if non_zero_since % 2 == 0:
                B = -last_pol
                V = B
                result.extend([B, 0, 0, V])
                last_pol = V
            else:
                V = last_pol
                result.extend([0, 0, 0, V])

            non_zero_since = 0
            i += 4
        else:
            result.append(0)
            i += 1

    return result
