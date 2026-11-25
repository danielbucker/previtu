"""Testes automatizados do site PreviTU V6.

Rodar:  python manage.py test predictor
"""
import csv
import io
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from . import motor_v6
from .models import Previsao

SEM_GRAM_OK = {
    "codigo_pedido": "TESTE-001",
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
}

COM_GRAM_OK = dict(
    SEM_GRAM_OK,
    codigo_pedido="TESTE-002",
    gram_bacterias_presentes="1",
    gram_bgn="1",
    gram_cgp="0",
    gram_levedura="0",
)


class ArtefatosV6Test(TestCase):
    def test_hash_confere_com_model_card(self):
        for via in ("sem_gram", "com_gram"):
            m = motor_v6.carregar(via)
            self.assertEqual(m.sha256, m.card["hashes"]["modelo_sha256"])


class SiteV6Test(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("ana", password="x-Teste-2026!")
        self.outro = User.objects.create_user("bia", password="x-Teste-2026!")
        self.client.force_login(self.u)

    def _post(self, via, dados):
        return self.client.post(f"/previsao/{via}/", dados, follow=True)

    def test_anonimo_vai_para_login(self):
        self.client.logout()
        r = self.client.get("/previsao/sem_gram/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_cada_via_usa_seu_artefato(self):
        self._post("sem_gram", SEM_GRAM_OK)
        self._post("com_gram", COM_GRAM_OK)
        sg = Previsao.objects.get(via="sem_gram")
        cg = Previsao.objects.get(via="com_gram")
        self.assertEqual(sg.modelo_sha256, motor_v6.carregar("sem_gram").sha256)
        self.assertEqual(cg.modelo_sha256, motor_v6.carregar("com_gram").sha256)
        self.assertNotEqual(sg.modelo_sha256, cg.modelo_sha256)

    def test_ausente_nao_vira_zero(self):
        sem = dict(SEM_GRAM_OK, codigo_pedido="T-20")
        sem.pop("UROT__SEDLEU")
        zero = dict(SEM_GRAM_OK, codigo_pedido="T-21", UROT__SEDLEU="0")
        self._post("sem_gram", sem)
        self._post("sem_gram", zero)
        a = Previsao.objects.get(codigo_pedido="T-20")
        b = Previsao.objects.get(codigo_pedido="T-21")
        self.assertIsNone(a.entrada["UROT__SEDLEU"])
        self.assertIn("UROT__SEDLEU", a.campos_ausentes)
        self.assertNotAlmostEqual(a.probabilidade, b.probabilidade, places=6)

    def test_codigo_com_nome_de_paciente_e_recusado(self):
        r = self._post("sem_gram", dict(SEM_GRAM_OK, codigo_pedido="Maria Silva"))
        self.assertEqual(Previsao.objects.count(), 0)
        self.assertIn("Não digite nome de paciente", r.content.decode())

    def test_outro_usuario_nao_ve_registro_alheio(self):
        self._post("sem_gram", SEM_GRAM_OK)
        p = Previsao.objects.get()
        self.client.force_login(self.outro)
        for url in (f"/resultado/{p.pk}/", f"/resultado/{p.pk}/informe/"):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.assertNotIn("TESTE-001", self.client.get("/historico/").content.decode())

    def test_csv_nao_executa_formula(self):
        self._post("sem_gram", dict(SEM_GRAM_OK, observacao="=HYPERLINK(1)"))
        texto = self.client.get("/historico/exportar/").content.decode("utf-8-sig")
        linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
        self.assertIn("'=HYPERLINK(1)", texto)
        for linha in linhas[1:]:
            for celula in linha:
                self.assertFalse(celula[:1] in ("=", "+", "@"), celula)

    def test_rotulos_da_interface(self):
        html = "".join(
            self.client.get(u).content.decode()
            for u in ("/", "/previsao/sem_gram/", "/previsao/com_gram/", "/sobre/")
        )
        self.assertNotIn("Predição de ITU", html)
        self.assertNotIn("XGBoost", html)
        self.assertIn("PreviTU V6", html)
        self.assertIn("urocultura positiva", html)
