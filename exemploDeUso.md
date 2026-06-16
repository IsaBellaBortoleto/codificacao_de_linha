# ═══════════════════════════════════════════════════════════════
# Exemplo de uso
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    bits  = [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1]  # 8 zeros entre dois 1s
    hdb3  = encode_hdb3(bits)
    volta = decode_hdb3(hdb3)

    print("Bits originais: ", bits)
    print("HDB3 codificado:", hdb3)
    print("Bits recuperados:", volta)
    print("Reversível:", bits == volta)
