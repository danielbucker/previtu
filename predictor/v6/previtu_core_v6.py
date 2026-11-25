"""Núcleo auditável do PreviTU V6 (motor HistGradientBoosting — Tese UFMG).

Uma única função pública (`prever`) que recebe os campos fisiológicos do EAS,
dados demográficos/assistenciais e, opcionalmente, os 4 marcadores qualitativos
do Gram morfológico, devolvendo probabilidade calibrada de urocultura positiva,
classe no limiar operacional, versão, hash SHA-256 do artefato e alertas de cautela.
Sem estado, sem rede, sem banco.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import joblib

BASE = Path(__file__).resolve().parent

VIAS = {
    "sem_gram": {
        "artefato": BASE / "previtu_v6_hgb_sem_gram.joblib",
        "card": BASE / "model_card_v6_sem_gram.json",
        "descricao": "EAS fisiológico (9 parâmetros) + demografia/origem (sem Gram)",
    },
    "com_gram": {
        "artefato": BASE / "previtu_v6_hgb_com_gram.joblib",
        "card": BASE / "model_card_v6_com_gram.json",
        "descricao": "EAS fisiológico (9 parâmetros) + demografia/origem + Gram morfológico (4 marcadores)",
    },
}

AVISO = (
    "Estimativa da probabilidade de urocultura POSITIVA (desfecho laboratorial). "
    "Não é diagnóstico de infecção do trato urinário, não indica antimicrobiano e "
    "não autoriza cancelar a cultura. Uso experimental, ensino e pesquisa."
)


@dataclass
class Resultado:
    probabilidade: float
    classe: str
    limiar: float
    regra_do_limiar: str
    versao: str
    modelo_sha256: str
    via: str = "sem_gram"
    alertas: list[str] = field(default_factory=list)
    campos_ausentes: list[str] = field(default_factory=list)
    aviso: str = AVISO

    def para_dict(self) -> dict:
        return asdict(self)


class PreviTU:
    def __init__(
        self,
        via: str = "sem_gram",
        regra_limiar: str = "sensibilidade_95",
        artefato: Path | None = None,
    ):
        if via not in VIAS:
            raise ValueError(f"Via desconhecida: {via!r}. Use 'sem_gram' ou 'com_gram'.")
        self.via = via
        self.descricao_da_via = VIAS[via]["descricao"]
        artefato = Path(artefato) if artefato is not None else VIAS[via]["artefato"]
        self._card_path = VIAS[via]["card"]

        pacote = joblib.load(artefato)
        self.pipeline = pacote["pipeline"]
        self.numericas = list(pacote["variaveis_numericas"])
        self.categoricas = list(pacote["variaveis_categoricas"])
        self.versao = str(pacote["versao"])
        self.regra_limiar = regra_limiar
        self.limiar = float(pacote["limiares"][regra_limiar])
        self.sha256 = self._sha(artefato)
        self.card = (
            json.loads(self._card_path.read_text(encoding="utf-8"))
            if self._card_path.exists()
            else {}
        )

    @staticmethod
    def _sha(caminho: Path) -> str:
        h = hashlib.sha256()
        with open(caminho, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    def _normalizar_entrada(self, entrada: dict) -> dict:
        """Harmoniza densidade (1015 -> 1.015) e calcula termo quadrático automaticamente."""
        dados = dict(entrada)
        if "UROT__GRAVID" in dados and dados["UROT__GRAVID"] is not None:
            g = float(dados["UROT__GRAVID"]) if isinstance(dados["UROT__GRAVID"], (int, float, np.number)) else pd.to_numeric(str(dados["UROT__GRAVID"]).replace(",", "."), errors="coerce")
            if pd.notna(g):
                if 1000.0 <= g <= 1060.0:
                    g = g / 1000.0
                if 1.000 <= g <= 1.060:
                    dados["UROT__GRAVID"] = float(g)
                    dados["UROT__GRAVID_DESVIO_QUAD"] = float((g - 1.015) ** 2)
                else:
                    dados["UROT__GRAVID"] = np.nan
                    dados["UROT__GRAVID_DESVIO_QUAD"] = np.nan
        return dados

    def _quadro(self, entrada: dict) -> tuple[pd.DataFrame, list[str]]:
        """Monta a linha na ordem exata do treino; campo ausente nunca vira zero."""
        dados = self._normalizar_entrada(entrada)
        linha, ausentes = {}, []
        for c in self.numericas:
            v = dados.get(c, None)
            if v is None or (isinstance(v, str) and not v.strip()):
                linha[c] = np.nan
                if c != "UROT__GRAVID_DESVIO_QUAD":
                    ausentes.append(c)
            else:
                num = float(v) if isinstance(v, (int, float, np.number)) else pd.to_numeric(str(v).replace(",", "."), errors="coerce")
                linha[c] = float(num) if pd.notna(num) else np.nan
                if pd.isna(linha[c]) and c != "UROT__GRAVID_DESVIO_QUAD":
                    ausentes.append(c)

        for c in self.categoricas:
            v = dados.get(c, None)
            if v is None or (isinstance(v, str) and not v.strip()):
                linha[c] = np.nan
                ausentes.append(c)
            else:
                linha[c] = str(v).strip()

        return pd.DataFrame([linha])[self.numericas + self.categoricas], ausentes

    def _alertas(self, entrada: dict, p: float, ausentes: list[str]) -> list[str]:
        a = []
        flora = pd.to_numeric(entrada.get("UROT__FLORA"), errors="coerce")
        leuc = pd.to_numeric(entrada.get("UROT__SEDLEU"), errors="coerce")

        if pd.notna(flora) and flora >= 1 and p < self.limiar:
            a.append("Flora aumentada com probabilidade estimada baixa: interpretar com cautela.")
        if pd.notna(flora) and flora >= 1 and pd.notna(leuc) and leuc < 5:
            a.append("Flora aumentada sem resposta inflamatória correspondente: considerar contaminação.")
        if len(ausentes) >= max(3, len(self.numericas) // 4):
            a.append(f"{len(ausentes)} campos não informados: estimativa apoiada em imputação.")
        if pd.notna(leuc) and leuc == 0 and p >= self.limiar:
            a.append("Ausência de leucocitúria com probabilidade elevada: revisar os dados digitados.")
        a.append("Os pesos do modelo expressam associação estatística, não causalidade.")
        return a

    def prever(self, entrada: dict) -> Resultado:
        X, ausentes = self._quadro(entrada)
        p = float(self.pipeline.predict_proba(X)[0, 1])
        classe = "acima_do_limiar" if p >= self.limiar else "abaixo_do_limiar"
        return Resultado(
            probabilidade=p,
            classe=classe,
            limiar=self.limiar,
            regra_do_limiar=self.regra_limiar,
            versao=self.versao,
            modelo_sha256=self.sha256,
            via=self.via,
            alertas=self._alertas(entrada, p, ausentes),
            campos_ausentes=ausentes,
        )

    def prever_lote(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.numericas + self.categoricas]
        return self.pipeline.predict_proba(X)[:, 1]
