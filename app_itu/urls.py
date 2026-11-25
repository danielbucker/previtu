from django.contrib import admin
from django.urls import include, path

from predictor import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/cadastro/", views.CadastroView.as_view(), name="cadastro"),

    path("", views.dashboard_view, name="dashboard"),
    path("previsao/", views.previsao_view, name="previsao"),
    path("previsao/<str:via>/", views.previsao_view, name="previsao_via"),
    path("resultado/<int:pk>/", views.resultado_view, name="resultado"),
    path("resultado/<int:pk>/informe/", views.informe_view, name="informe"),
    path("historico/", views.historico_view, name="historico"),
    path("historico/exportar/", views.exportar_csv_view, name="exportar_historico"),
    path("sobre/", views.sobre_view, name="sobre"),
]
