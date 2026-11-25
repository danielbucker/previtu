"""Testes de auditoria do PreviTU V6 (motor HistGradientBoosting — 2023–2024)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from previtu_core_v6 import PreviTU, VIAS

BASE = Path(__file__).resolve().parent


def carregar_amostra(amostra_path: Path, cat_cols: list[str]) -> pd.DataFrame:
    # float_precision='round_trip' garante reconstrução bit-a-bit exata dos floats (essencial para árvores HGB)
    dtype_map = {c: str for c in cat_cols}
    df = pd.read_csv(amostra_path, dtype=dtype_map, keep_default_na=True, float_precision="round_trip")
    for c in cat_cols:
        s = df[c].astype(str).str.strip()
        df[c] = np.where(df[c].isna() | s.isin(["", "nan", "NaN", "None", "NONE", "<NA>"]), np.nan, s)
    return df


def rodar_auditoria(via: str) -> list[str]:
    m = PreviTU(via=via, regra_limiar="sensibilidade_95")
    amostra_path = BASE / f"amostra_auditoria_2023_2024_v6_{via}.csv.gz"
    esperado_path = BASE / f"predicoes_2023_2024_v6_{via}.npy"
    card_path = VIAS[via]["card"]
    if not (amostra_path.exists() and esperado_path.exists()):
        print("Amostra de auditoria 2023–2024 ausente: ela contém dados de pacientes e não é distribuída "
              "neste repositório. Teste de reprodução exata pulado.")
        return []

    t = carregar_amostra(amostra_path, m.categoricas)
    esperado = np.load(esperado_path)
    card = json.loads(card_path.read_text(encoding="utf-8"))
    falhas = []

    # 1. Reprodução em lote (< 1e-9)
    obtido = m.prever_lote(t)
    d_max = float(np.max(np.abs(obtido - esperado)))
    print(f"[1] Lote 2023–2024 (n={len(t)}): diferença máxima = {d_max:.3e}")
    if d_max > 1e-9:
        falhas.append(f"lote diverge das predições congeladas ({d_max:.3e})")

    # 2. Reprodução registro a registro pela interface pública
    sub = t.sample(min(200, len(t)), random_state=42)
    difs = []
    for idx, row in sub.iterrows():
        entrada = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        difs.append(abs(m.prever(entrada).probabilidade - esperado[idx]))
    print(f"[2] {len(sub)} registros pela interface pública: diferença máxima = {max(difs):.3e}")
    if max(difs) > 1e-9:
        falhas.append(f"interface unitária diverge do lote ({max(difs):.3e})")

    # 3. Ausência nunca vira zero
    base = {k: (None if pd.isna(v) else v) for k, v in t.iloc[0].to_dict().items()}
    sem_leuc = {k: v for k, v in base.items() if k != "UROT__SEDLEU"}
    com_zero = dict(base, UROT__SEDLEU=0.0)
    r_aus = m.prever(sem_leuc)
    r_zero = m.prever(com_zero)
    print(f"[3] UROT__SEDLEU ausente={r_aus.probabilidade:.6f} vs. zero={r_zero.probabilidade:.6f}")
    if "UROT__SEDLEU" not in r_aus.campos_ausentes:
        falhas.append("campo ausente não declarado em campos_ausentes")

    # 4. Limiar e SHA-256 coerentes com o model card
    r0 = m.prever(base)
    print(f"[4] Limiar={r0.limiar:.6f} | Versão={r0.versao} | SHA256={r0.modelo_sha256[:12]}...")
    if abs(r0.limiar - card["limiares"]["sensibilidade_95"]) > 1e-12:
        falhas.append("limiar diverge do model card")
    if r0.modelo_sha256 != card["hashes"]["modelo_sha256"]:
        falhas.append("SHA-256 do artefato diverge do model card")

    # 5. Reprodução da AUROC no conjunto temporal 2023–2024
    auc = float(roc_auc_score(t["Cultura_positiva"].to_numpy(), obtido))
    auc_card = float(card["desempenho_2023_2024"]["auroc"])
    print(f"[5] AUROC 2023–2024 recalculada = {auc:.6f} (card = {auc_card:.6f})")
    if abs(auc - auc_card) > 1e-6:
        falhas.append("AUROC diverge do model card")

    return falhas


def main() -> int:
    todas = []
    for via in ("sem_gram", "com_gram"):
        print(f"\n=== AUDITORIA VIA: {via} ({VIAS[via]['descricao']}) ===")
        todas.extend([f"[{via}] {f}" for f in rodar_auditoria(via)])
    print("\nRESULTADO FINAL:", "TODOS OS TESTES PASSARAM" if not todas else f"FALHAS: {todas}")
    return 1 if todas else 0


if __name__ == "__main__":
    raise SystemExit(main())
