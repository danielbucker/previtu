import csv
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic.edit import CreateView

from . import campos, motor_v6
from .models import Previsao

RE_CODIGO = re.compile(r"^(?=.*\d)[A-Za-z0-9._-]{3,40}$")


def _visiveis(user):
    qs = Previsao.objects.select_related("usuario")
    return qs if (user.is_staff or user.is_superuser) else qs.filter(usuario=user)


@login_required
def dashboard_view(request):
    return render(request, "dashboard.html", {
        "ultima": _visiveis(request.user).first(),
        "total": _visiveis(request.user).count(),
        "sem_gram": motor_v6.resumo_card("sem_gram"),
        "com_gram": motor_v6.resumo_card("com_gram"),
    })


@login_required
def previsao_view(request, via="sem_gram"):
    if via not in campos.CAMPOS:
        via = "sem_gram"
    valores, erros = {}, []

    if request.method == "POST":
        valores = request.POST
        codigo = (request.POST.get("codigo_pedido") or "").strip()
        if not RE_CODIGO.match(codigo):
            erros.append(
                "Código do pedido: use um código pseudonimizado (sem espaços, com ao menos um número). "
                "Não digite nome de paciente."
            )
        entrada, erros_campos = campos.ler_formulario(via, request.POST)
        erros += erros_campos
        if not erros:
            r = motor_v6.classificar(via, entrada)
            p = Previsao.objects.create(
                usuario=request.user,
                codigo_pedido=codigo,
                observacao=(request.POST.get("observacao") or "").strip()[:300],
                via=via,
                entrada=entrada,
                campos_ausentes=r["campos_ausentes"],
                probabilidade=r["probabilidade"],
                classe=r["classe"],
                limiar_efetivo=r["limiar_efetivo"],
                limiar_card=r["limiar_card"],
                regra_do_limiar=r["regra_do_limiar"],
                versao_modelo=r["versao_modelo"],
                modelo_sha256=r["modelo_sha256"],
                versao_site=motor_v6.VERSAO_SITE,
                alertas=r["alertas"],
            )
            return redirect("resultado", pk=p.pk)
    elif request.GET.get("exemplo") == "1":
        sufixo = "COM-GRAM-01" if via == "com_gram" else "SEM-GRAM-01"
        valores = dict(campos.EXEMPLO[via], codigo_pedido=f"DEMO-{sufixo}")

    return render(request, "previsao.html", {
        "via": via,
        "secoes": campos.secoes(via),
        "valores": valores,
        "erros": erros,
        "card": motor_v6.resumo_card(via),
    })


def _entrada_legivel(p):
    rotulos = {c["nome"]: c for c in campos.CAMPOS[p.via]}
    linhas = []
    for nome, c in rotulos.items():
        v = p.entrada.get(nome)
        if v is None:
            texto = "não informado"
        elif c["tipo"] == "select":
            chave = v if isinstance(v, str) else f"{v:g}"
            texto = dict(c["opcoes"]).get(chave, str(v))
        else:
            texto = f"{v:g}".replace(".", ",")
        linhas.append((c["rotulo"], texto))
    return linhas


def _pode_ver(user, p):
    return p.usuario_id == user.id or user.is_staff or user.is_superuser


@login_required
def resultado_view(request, pk):
    p = get_object_or_404(Previsao, pk=pk)
    if not _pode_ver(request.user, p):
        messages.error(request, "Você não tem permissão para ver este registro.")
        return redirect("historico")
    return render(request, "resultado.html", {
        "p": p, "linhas": _entrada_legivel(p), "card": motor_v6.resumo_card(p.via),
    })


@login_required
def informe_view(request, pk):
    p = get_object_or_404(Previsao, pk=pk)
    if not _pode_ver(request.user, p):
        messages.error(request, "Você não tem permissão para ver este registro.")
        return redirect("historico")
    return render(request, "informe.html", {
        "p": p, "linhas": _entrada_legivel(p), "card": motor_v6.resumo_card(p.via),
        "gerado_em": timezone.now(),
    })


@login_required
def historico_view(request):
    return render(request, "historico.html", {"previsoes": _visiveis(request.user)})


def _celula_segura(valor):
    """Evita que o Excel interprete a célula como fórmula (=, +, -, @)."""
    texto = "" if valor is None else str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


@login_required
def exportar_csv_view(request):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="previtu_v6_historico.csv"'
    resp.write("\ufeff")
    w = csv.writer(resp, delimiter=";")
    w.writerow(["Data", "Usuário", "Código do pedido", "Via", "Probabilidade", "Classe",
                "Limiar efetivo", "Modelo", "SHA-256", "Campos ausentes", "Alertas", "Observação"])
    for p in _visiveis(request.user):
        w.writerow([_celula_segura(x) for x in [
            timezone.localtime(p.criado_em).strftime("%d/%m/%Y %H:%M"), p.usuario.username,
            p.codigo_pedido, p.get_via_display(), f"{p.probabilidade:.6f}", p.get_classe_display(),
            f"{p.limiar_efetivo:.10f}", p.versao_modelo, p.modelo_sha256,
            ", ".join(p.campos_ausentes), " | ".join(p.alertas), p.observacao]])
    return resp


@login_required
def sobre_view(request):
    return render(request, "sobre.html", {
        "sem_gram": motor_v6.resumo_card("sem_gram"),
        "com_gram": motor_v6.resumo_card("com_gram"),
        "versao_site": motor_v6.VERSAO_SITE,
    })


class CadastroView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/cadastro.html"

    def dispatch(self, request, *args, **kwargs):
        if not settings.CADASTRO_PUBLICO_ABERTO:
            messages.error(request, "O cadastro de novos usuários está desativado. Solicite acesso ao administrador.")
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)
