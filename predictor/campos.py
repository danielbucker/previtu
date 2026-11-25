"""Campos de entrada das duas vias do PreviTU V6 (HistGradientBoosting).

Os nomes internos correspondem exatamente às colunas congeladas no pipeline V6:
- 3 variáveis demográficas/assistenciais: Idade_anos, Sexo, Origem
- 9 parâmetros fisiológicos do EAS: UROT__PH, UROT__GRAVID (+ termo quadrático
  calculado automaticamente no núcleo), UROT__ESTERASE, UROT__NITRIT,
  UROT__HEMOGL, UROT__GLIC, UROT__SEDLEU, UROT__SEDHEM, UROT__FLORA
- 4 marcadores qualitativos do Gram (via com_gram): gram_bacterias_presentes,
  gram_bgn, gram_cgp, gram_levedura
"""

FITA = [
    ("0", "Negativo"),
    ("0.5", "Traços"),
    ("1", "+"),
    ("2", "++"),
    ("3", "+++"),
    ("4", "++++"),
]

FLORA = [
    ("0", "Ausente / negativa"),
    ("1", "Escassa / leve (+)"),
    ("2", "Moderada (++)"),
    ("3", "Acentuada / numerosa (+++)"),
    ("4", "Maciça (++++)"),
]

# Valores exatos codificados no OneHotEncoder do pipeline V6
NITRITO = [
    ("Negativo", "Negativo"),
    ("Positivo", "Positivo"),
]

ORIGEM = [
    ("BC", "BC — ambulatorial"),
    ("HC", "HC — internação"),
    ("PA", "PA — pronto atendimento"),
    ("JAF", "JAF"),
    ("LEXT", "LEXT"),
    ("SAST", "SAST"),
]

SEXO = [
    ("F", "Feminino"),
    ("M", "Masculino"),
]

BINARIO_GRAM = [
    ("0", "Ausente"),
    ("1", "Presente"),
]

CATEGORICAS_STR = {"Sexo", "Origem", "UROT__NITRIT"}


def _sel(nome, rotulo, opcoes, secao, ajuda=""):
    return {"nome": nome, "rotulo": rotulo, "tipo": "select", "opcoes": opcoes, "secao": secao, "ajuda": ajuda}


def _num(nome, rotulo, secao, passo="any", minimo=None, maximo=None, ajuda=""):
    return {
        "nome": nome, "rotulo": rotulo, "tipo": "numero", "passo": passo,
        "min": minimo, "max": maximo, "secao": secao, "ajuda": ajuda,
    }


CAMPOS_SEM_GRAM = [
    _num("Idade_anos", "Idade (anos)", "Paciente e origem", passo="0.1", minimo=0, maximo=120,
         ajuda="Aceita fração de ano (ex.: 0,5 para 6 meses)."),
    _sel("Sexo", "Sexo", SEXO, "Paciente e origem"),
    _sel("Origem", "Origem do pedido", ORIGEM, "Paciente e origem", ajuda="Código do setor no SIL."),

    _num("UROT__PH", "pH urinário", "Exame físico e tira reagente", passo="0.5", minimo=4.0, maximo=10.0),
    _num("UROT__GRAVID", "Densidade urinária", "Exame físico e tira reagente", passo="0.001", minimo=1.000, maximo=1.060,
         ajuda="Ex.: 1,015 (ou 1015). O desvio quadrático de 1,015 é calculado automaticamente."),
    _sel("UROT__ESTERASE", "Esterase leucocitária", FITA, "Exame físico e tira reagente"),
    _sel("UROT__NITRIT", "Nitrito", NITRITO, "Exame físico e tira reagente"),
    _sel("UROT__HEMOGL", "Hemoglobina (fita)", FITA, "Exame físico e tira reagente"),
    _sel("UROT__GLIC", "Glicose (fita)", FITA, "Exame físico e tira reagente"),

    _num("UROT__SEDLEU", "Leucócitos no sedimento (por campo)", "Sedimentoscopia", passo="0.5", minimo=0,
         ajuda="Para 'numerosos/incontáveis', use 100."),
    _num("UROT__SEDHEM", "Hemácias no sedimento (por campo)", "Sedimentoscopia", passo="0.5", minimo=0,
         ajuda="Para 'numerosas/incontáveis', use 100."),
    _sel("UROT__FLORA", "Flora bacteriana", FLORA, "Sedimentoscopia"),
]

CAMPOS_GRAM = [
    _sel("gram_bacterias_presentes", "Bactérias presentes no Gram", BINARIO_GRAM, "Gram morfológico (4 marcadores)",
         ajuda="Deixe em branco se o Gram não foi realizado."),
    _sel("gram_bgn", "Bacilos Gram-negativos (BGN)", BINARIO_GRAM, "Gram morfológico (4 marcadores)"),
    _sel("gram_cgp", "Cocos Gram-positivos (CGP)", BINARIO_GRAM, "Gram morfológico (4 marcadores)"),
    _sel("gram_levedura", "Leveduras / fungos", BINARIO_GRAM, "Gram morfológico (4 marcadores)"),
]

CAMPOS_COM_GRAM = CAMPOS_SEM_GRAM + CAMPOS_GRAM

CAMPOS = {
    "sem_gram": CAMPOS_SEM_GRAM,
    "com_gram": CAMPOS_COM_GRAM,
}

# Casos fictícios (não representam pacientes reais) para demonstração.
EXEMPLO = {
    "sem_gram": {
        "Idade_anos": "58",
        "Sexo": "F",
        "Origem": "BC",
        "UROT__PH": "6.0",
        "UROT__GRAVID": "1.018",
        "UROT__ESTERASE": "2",
        "UROT__NITRIT": "Positivo",
        "UROT__HEMOGL": "1",
        "UROT__GLIC": "0",
        "UROT__SEDLEU": "35",
        "UROT__SEDHEM": "4",
        "UROT__FLORA": "2",
    },
    "com_gram": {
        "Idade_anos": "58",
        "Sexo": "F",
        "Origem": "BC",
        "UROT__PH": "6.0",
        "UROT__GRAVID": "1.018",
        "UROT__ESTERASE": "2",
        "UROT__NITRIT": "Positivo",
        "UROT__HEMOGL": "1",
        "UROT__GLIC": "0",
        "UROT__SEDLEU": "35",
        "UROT__SEDHEM": "4",
        "UROT__FLORA": "2",
        "gram_bacterias_presentes": "1",
        "gram_bgn": "1",
        "gram_cgp": "0",
        "gram_levedura": "0",
    },
}


def secoes(via: str):
    ordem, grupos = [], {}
    for c in CAMPOS[via]:
        if c["secao"] not in grupos:
            ordem.append(c["secao"])
            grupos[c["secao"]] = []
        grupos[c["secao"]].append(c)
    return [(s, grupos[s]) for s in ordem]


def ler_formulario(via: str, post):
    """Converte o POST no dicionário esperado por previtu_core_v6.PreviTU.

    Campo numérico ou select em branco -> None (imputado pelo pipeline com indicador
    de ausência; nunca vira zero).
    """
    entrada, erros = {}, []
    for c in CAMPOS[via]:
        nome = c["nome"]
        bruto = (post.get(nome) or "").strip()
        if c["tipo"] != "select" or nome not in CATEGORICAS_STR:
            bruto = bruto.replace(",", ".")
        if bruto == "":
            entrada[nome] = None
            continue
        if c["tipo"] == "select":
            validos = {v for v, _ in c["opcoes"]}
            if bruto not in validos:
                erros.append(f"{c['rotulo']}: valor fora das opções.")
                continue
            entrada[nome] = bruto if nome in CATEGORICAS_STR else float(bruto)
        else:
            try:
                v = float(bruto)
            except ValueError:
                erros.append(f"{c['rotulo']}: valor não numérico.")
                continue
            if nome == "UROT__GRAVID" and 1000.0 <= v <= 1060.0:
                v = v / 1000.0
            if (c["min"] is not None and v < c["min"]) or (c["max"] is not None and v > c["max"]):
                erros.append(f"{c['rotulo']}: fora do intervalo aceito ({c['min']}–{c['max']}).")
                continue
            entrada[nome] = v

    for obrig in ("Idade_anos", "Sexo", "Origem"):
        if entrada.get(obrig) is None:
            rot = next(c["rotulo"] for c in CAMPOS[via] if c["nome"] == obrig)
            erros.append(f"{rot} é obrigatório.")
    return entrada, erros
