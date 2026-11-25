from django.conf import settings


def cadastro_aberto(request):
    """
    Expoe a flag do auto-cadastro publico aos templates, para esconder o link
    "Ainda nao tenho cadastro" quando o site esta exposto. E apenas cosmetico:
    o bloqueio efetivo esta na CadastroView.
    """
    return {
        "cadastro_aberto": getattr(settings, "CADASTRO_PUBLICO_ABERTO", True),
    }
