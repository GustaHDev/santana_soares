from django.contrib import admin
from django.urls import path

from usuarios.admin import motorista_admin_site

admin.site.site_header = "Sistema de Viagens"
admin.site.site_title = "Viagens"
admin.site.index_title = "Painel Administrativo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("motorista/", motorista_admin_site.urls),
]
