"""Ponte entre o site Django e o núcleo congelado do PreviTU V6 (HistGradientBoosting).

O núcleo (`v6/previtu_core_v6.py`) e os dois artefatos (`v6/*.joblib`) são usados
exatamente como foram congelados: nenhum byte deles é alterado aqui.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

V6_DIR = Path(__file__).resolve().parent / "v6"
if str(V6_DIR) not in sys.path:
    sys.path.insert(0, str(V6_DIR))

from previtu_core_v6 import PreviTU  # noqa: E402

VERSAO_SITE = "PreviTU V6 — protótipo da tese (HistGradientBoosting, 2026)"

ROTULO_VIA = {
    "sem_gram": "Via sem Gram — 9 parâmetros fisiológicos do EAS + demografia/origem (HGB)",
    "com_gram": "Via com Gram — EAS fisiológico + demografia/origem + 4 marcadores do Gram (HGB)",
}

# Métricas operacionais congeladas na validação temporal 2023–2024 (n=9.425 pacientes novos; 2.174 positivas)
# no limiar de sensibilidade >= 95% derivado em 2011–2022.
DESEMPENHO_OPERACIONAL_2023_2024 = {
    "sem_gram": {
        "n_positivas": 2174,
        "roc_auc_ic95": (0.8776, 0.8961),
        "cal_intercepto": 0.042,
        "cal_inclinacao": 1.078,
        "sensibilidade": 0.968261,
        "especificidade": 0.284237,
        "vpn": 0.967606,
        "abaixo_pct": 22.5995,
        "fn_por_mil": 7.3210,
    },
    "com_gram": {
        "n_positivas": 2174,
        "roc_auc_ic95": (0.9049, 0.9213),
        "cal_intercepto": 0.028,
        "cal_inclinacao": 1.068,
        "sensibilidade": 0.978381,
        "especificidade": 0.310854,
        "vpn": 0.979574,
        "abaixo_pct": 24.4138,
        "fn_por_mil": 4.9867,
    },
}

LIMITACOES_V6 = [
    "Validação temporal no mesmo serviço (HC-UFMG/Ebserh, 2023–2024 em pacientes inéditos); sem validação externa geográfica.",
    "Sem avaliação prospectiva silenciosa, de usabilidade ou de impacto clínico-operacional.",
    "Estima exclusivamente positividade microbiológica da urocultura — não diagnostica ITU clínica nem orienta antimicrobiano.",
    "Gestação, transplante renal, uropatia estrutural/cateterismo e crianças pequenas exigem interpretação clínica independente do limiar.",
]


class ArtefatoInvalido(RuntimeError):
    pass


@lru_cache(maxsize=None)
def carregar(via: str) -> PreviTU:
    """Carrega a via solicitada e recusa artefato cujo SHA-256 divirja do model card."""
    m = PreviTU(via=via, regra_limiar="sensibilidade_95")
    card_hash = m.card.get("hashes", {}).get("modelo_sha256")
    if card_hash and card_hash != m.sha256:
        raise ArtefatoInvalido(f"SHA-256 do artefato da via {via} não confere com o model card.")
    return m


def limiar_efetivo(via: str) -> float:
    return carregar(via).limiar


def classificar(via: str, entrada: dict) -> dict:
    """Executa o núcleo congelado V6 e devolve o dicionário gravado e exibido pelo site."""
    m = carregar(via)
    r = m.prever(entrada)
    corte = m.limiar
    acima = r.probabilidade >= corte
    return {
        "via": via,
        "probabilidade": r.probabilidade,
        "acima_do_limiar": acima,
        "classe": "acima" if acima else "abaixo",
        "limiar_card": r.limiar,
        "limiar_efetivo": corte,
        "regra_do_limiar": r.regra_do_limiar,
        "versao_modelo": f"{r.versao} · {m.card.get('algoritmo', 'HistGradientBoostingClassifier')}",
        "modelo_sha256": r.modelo_sha256,
        "campos_ausentes": list(r.campos_ausentes),
        "alertas": list(r.alertas),
    }


def resumo_card(via: str) -> dict:
    """Consolida os números do model card V6 e da validação temporal 2023–2024."""
    m = carregar(via)
    c = m.card
    d = c["desempenho_2023_2024"]
    op = DESEMPENHO_OPERACIONAL_2023_2024[via]
    num_vars = [v for v in c["variaveis_numericas"] if v != "UROT__GRAVID_DESVIO_QUAD"]
    cat_vars = list(c["variaveis_categoricas"])
    return {
        "via": via,
        "rotulo": ROTULO_VIA[via],
        "algoritmo": c.get("algoritmo", "HistGradientBoostingClassifier"),
        "versao": c.get("versao", m.versao),
        "n_variaveis": len(num_vars) + len(cat_vars),
        "variaveis": num_vars + cat_vars,
        "treino": c["coorte_desenvolvimento"],
        "teste": {
            "periodo": c["coorte_teste_temporal"]["periodo"],
            "n_pedidos": c["coorte_teste_temporal"]["n_pedidos"],
            "n_positivas": op["n_positivas"],
        },
        "roc_auc": d["auroc"],
        "roc_auc_ic95": op["roc_auc_ic95"],
        "pr_auc": d["pr_auc"],
        "brier": d["brier"],
        "cal_intercepto": op["cal_intercepto"],
        "cal_inclinacao": op["cal_inclinacao"],
        "sensibilidade": op["sensibilidade"],
        "especificidade": op["especificidade"],
        "vpn": op["vpn"],
        "abaixo_pct": op["abaixo_pct"],
        "fn_por_mil": op["fn_por_mil"],
        "limiar_card": c["limiares"]["sensibilidade_95"],
        "limiar_efetivo": m.limiar,
        "limiar_youden": c["limiares"].get("youden"),
        "sha256": m.sha256,
        "congelado_em": c.get("gerado_em_utc", "")[:10],
        "limitacoes": LIMITACOES_V6,
        "sklearn_version": c.get("sklearn_version", ""),
        "hiperparametros": c.get("hiperparametros", {}),
    }
