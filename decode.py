# ═══════════════════════════════════════════════════════════════
# HDB3 — Decoder
# ═══════════════════════════════════════════════════════════════

def decode_hdb3(hdb3: list[int]) -> list[int]:
    """
    Decodifica símbolos HDB3 (-1, 0, +1) de volta para bits (0/1).

    Percorre o sinal procurando violações AMI (pulso com mesma
    polaridade do pulso não-zero anterior) e remove as substituições:
      000V → zera os 4 símbolos
      B00V → zera o B e o V
    """
    temp     = hdb3[:]
    last_pol = 0

    for i in range(len(temp)):
        if temp[i] == 0:
            continue

        if last_pol != 0 and temp[i] == last_pol:
            # Violação detectada → identificar padrão
            if i >= 3:
                case_000V = (temp[i-1] == 0 and temp[i-2] == 0 and temp[i-3] == 0)
                case_B00V = (temp[i-1] == 0 and temp[i-2] == 0 and temp[i-3] != 0)

                if case_000V:
                    temp[i] = 0
                elif case_B00V:
                    temp[i-3] = 0
                    temp[i]   = 0
            # last_pol não muda — o V foi removido
        else:
            last_pol = temp[i]

    # AMI limpo → bits
    return [1 if s != 0 else 0 for s in temp]

