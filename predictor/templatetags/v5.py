from django import template

register = template.Library()


@register.filter
def pct(valor, casas=1):
    """0.0489 -> '4,9%'. Aceita None."""
    if valor is None:
        return "—"
    return f"{float(valor) * 100:.{int(casas)}f}%".replace(".", ",")


@register.filter
def num(valor, casas=3):
    if valor is None:
        return "—"
    return f"{float(valor):.{int(casas)}f}".replace(".", ",")


@register.filter
def curto(sha, n=12):
    return (sha or "")[: int(n)]


@register.filter
def css_pct(valor):
    """0.0489 -> '4.89' (para style=left:...%), limitado a 0-100."""
    v = max(0.0, min(100.0, float(valor) * 100))
    return f"{v:.2f}"


@register.filter
def milhar(valor):
    return f"{int(valor):,}".replace(",", ".")
