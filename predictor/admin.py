from django.contrib import admin

from .models import Previsao


@admin.register(Previsao)
class PrevisaoAdmin(admin.ModelAdmin):
    list_display = ("id", "criado_em", "usuario", "codigo_pedido", "via", "probabilidade", "classe")
    list_filter = ("via", "classe", "usuario")
    search_fields = ("codigo_pedido", "usuario__username")

    # Registro de auditoria: somente leitura no admin.
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
