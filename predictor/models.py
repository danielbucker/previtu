from django.contrib.auth.models import User
from django.db import models


class Previsao(models.Model):
    """Uma estimativa do PreviTU V6, com tudo o que é preciso para auditá-la."""

    VIAS = [
        ("sem_gram", "Via sem Gram (EAS fisiológico · HGB)"),
        ("com_gram", "Via com Gram (EAS + Gram morfológico · HGB)"),
    ]
    CLASSES = [
        ("acima", "Acima do limiar de triagem"),
        ("abaixo", "Abaixo do limiar de triagem"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="previsoes")
    criado_em = models.DateTimeField(auto_now_add=True)

    codigo_pedido = models.CharField(max_length=40)
    observacao = models.CharField(max_length=300, blank=True)

    via = models.CharField(max_length=15, choices=VIAS)
    entrada = models.JSONField()
    campos_ausentes = models.JSONField(default=list)

    probabilidade = models.FloatField()
    classe = models.CharField(max_length=10, choices=CLASSES)
    limiar_efetivo = models.FloatField()
    limiar_card = models.FloatField()
    regra_do_limiar = models.CharField(max_length=40)
    versao_modelo = models.CharField(max_length=120)
    modelo_sha256 = models.CharField(max_length=64)
    versao_site = models.CharField(max_length=120)
    alertas = models.JSONField(default=list)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.codigo_pedido} · {self.get_via_display()} · {self.probabilidade:.4f}"

    @property
    def percentual(self):
        return self.probabilidade * 100

    @property
    def limiar_percentual(self):
        return self.limiar_efetivo * 100
