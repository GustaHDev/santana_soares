from django.contrib import admin

from .models import Cidade, Cliente, ClienteCidade


@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ("nome", "uf", "ativo")
    list_filter = ("uf", "ativo")
    search_fields = ("nome",)
    list_editable = ("ativo",)


class ClienteCidadeInline(admin.TabularInline):
    model = ClienteCidade
    extra = 1
    fields = ("cidade", "preco_tonelada", "ativo")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "faz_cte", "ativo")
    list_filter = ("faz_cte", "ativo")
    search_fields = ("nome",)
    list_editable = ("ativo",)
    inlines = [ClienteCidadeInline]


@admin.register(ClienteCidade)
class ClienteCidadeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "preco_tonelada", "ativo")
    list_filter = ("ativo", "cidade__uf")
    search_fields = ("cliente__nome", "cidade__nome")
    raw_id_fields = ("cliente", "cidade")
    list_editable = ("ativo",)

    def has_delete_permission(self, request, obj=None):
        return False
