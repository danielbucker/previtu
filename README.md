# PreviTU V6 — estimativa da probabilidade de urocultura positiva

Protótipo web experimental desenvolvido na tese de doutorado de **Daniel Henrique Bücker** (Programa de Pós-Graduação em Ciências Aplicadas à Saúde do Adulto, Faculdade de Medicina da UFMG; orientador: Prof. Leonardo de Souza Vasconcellos). A partir do exame de urina rotina (EAS), de idade, sexo e origem assistencial, e opcionalmente de quatro achados qualitativos da bacterioscopia pelo Gram, o PreviTU estima a probabilidade calibrada de a urocultura quantitativa ser positiva.

> **Aviso.** Software de pesquisa. Não é dispositivo médico, não foi validado prospectivamente e não deve ser usado para decidir sozinho a realização, o cancelamento ou a interpretação de exames, nem a conduta clínica. Não insira dados identificáveis de pacientes.

Os códigos de análise da tese (treinamento, validação temporal e externa, escore) e uma base sintética de teste estão em <https://github.com/danielbucker/tese-urocultura-ml-hcufmg>.

## Duas vias de inferência

| Via | Entradas | Modelo congelado | AUROC 2023–2024 (pacientes novos, n = 9.425 pedidos) | Limiar de sensibilidade ≥ 95% | SHA-256 |
|---|---|---|---|---|---|
| `sem_gram` | 9 parâmetros do EAS + idade, sexo, origem | `previtu_v6_hgb_sem_gram.joblib` | 0,8863 | 5,36% | `462aded6ff5d…` |
| `com_gram` | os mesmos + 4 marcadores qualitativos do Gram | `previtu_v6_hgb_com_gram.joblib` | 0,9132 | 4,85% | `94e97bb9e72e…` |

Os dois modelos são `HistGradientBoostingClassifier` (scikit-learn 1.7.2), treinados com pedidos de 2011 a 2022 do Laboratório de Análises Clínicas do HC-UFMG e congelados. Hiperparâmetros, limiares, métricas e hashes completos estão em `predictor/v6/model_card_v6_*.json`.

## Estrutura

```
app_itu/                 configuração do Django
predictor/               aplicativo (formulários, telas, histórico, exportação CSV)
predictor/v6/            núcleo de inferência e artefatos congelados
  previtu_core_v6.py     núcleo auditável, sem estado (função pública `prever`)
  *.joblib               modelos congelados
  model_card_v6_*.json   metadados, limiares, métricas e SHA-256
  teste_previtu_core_v6_exact.py  auditoria numérica do núcleo
static/                  CSS e bibliotecas front-end (Bootstrap, Bootstrap Icons; licença MIT)
```

## Como rodar

Requer Python 3.11 ou superior.

```bash
python -m venv venv_previtu_v6
# Windows: venv_previtu_v6\Scripts\activate    Linux/macOS: source venv_previtu_v6/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

No Windows, depois de criar o ambiente, basta dar duplo clique em `INICIAR_PREVITU_V6.bat`.

Configuração por variáveis de ambiente: `DJANGO_SECRET_KEY` (obrigatória para uso continuado; sem ela, uma chave aleatória é gerada a cada execução), `DJANGO_DEBUG` (padrão `False`) e `DJANGO_ALLOWED_HOSTS` (padrão `127.0.0.1,localhost`).

## Uso do núcleo sem o site

```python
import sys; sys.path.insert(0, "predictor/v6")
from previtu_core_v6 import PreviTU

m = PreviTU(via="sem_gram", regra_limiar="sensibilidade_95")
r = m.prever({"Idade_anos": 58, "Sexo": "F", "Origem": "BC", "UROT__PH": 6.0,
              "UROT__GRAVID": 1018, "UROT__ESTERASE": 2, "UROT__NITRIT": "Positivo",
              "UROT__HEMOGL": 1, "UROT__GLIC": 0, "UROT__SEDLEU": 35,
              "UROT__SEDHEM": 4, "UROT__FLORA": 2})
print(r.probabilidade, r.classe, r.modelo_sha256[:12], r.alertas)
```

Campos não informados permanecem ausentes e recebem a regra de imputação aprendida no desenvolvimento; nunca são convertidos em zero.

## Testes

```bash
python manage.py test predictor                     # 8 testes do site
python predictor/v6/teste_previtu_core_v6_exact.py  # auditoria do núcleo
```

A auditoria completa compara o núcleo com as 9.425 predições congeladas de 2023–2024 (diferença máxima < 10⁻⁹). Essa amostra contém dados de pacientes e **não é distribuída**; sem ela, o teste de reprodução exata é pulado.

## Limitações conhecidas

- **Escala da flora bacteriana.** No laboratório de origem, a flora é registrada como escassa, moderada ou aumentada. Durante o treinamento, o termo "aumentada" não foi convertido para a escala numérica e entrou no modelo como valor ausente. Em consequência, **para o modelo, deixar o campo de flora em branco equivale a informar flora aumentada**, e o nível "+++" da interface corresponde a uma combinação rara no treino. Detalhes na Seção 5.3 da tese. Uma versão retreinada com a conversão corrigida está prevista.
- Modelo derivado de um único hospital universitário brasileiro, em estudo retrospectivo e sem variáveis clínicas. Em outros serviços, exige harmonização do fluxo de microscopia (universal vs. reflexa) e recalibração local (Seção 5.4 da tese).
- No limiar de alta sensibilidade, a especificidade é baixa (28% a 31%): o uso previsto é apenas de triagem de exclusão (*rule-out*), com exclusão de gestantes, transplantados renais, pacientes com uropatia ou cateterismo e crianças pequenas.

## Como citar

BÜCKER, D. H. *Perfil demográfico, espectro microbiológico e potencial preditivo dos testes de urina rotina e bacterioscopia nos resultados de uroculturas ambulatoriais e hospitalares de pacientes assistidos em serviço público de Minas Gerais*. Tese (Doutorado em Ciências Aplicadas à Saúde do Adulto) — Faculdade de Medicina, Universidade Federal de Minas Gerais, Belo Horizonte, 2026.

## Licença

MIT — Copyright (c) 2026 Daniel Henrique Bücker. Ver `LICENSE`. Bootstrap e Bootstrap Icons mantêm suas próprias licenças MIT em `static/vendor/`.
