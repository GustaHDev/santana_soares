from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import MotoristaInlineForm, UsuarioChangeForm, UsuarioCreationForm
from .models import Motorista, Papel, Usuario


class MotoristaAdminSite(admin.AdminSite):
    site_header = "Painel do Motorista"
    site_title = "Motorista"
    index_title = "Minhas Viagens"

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_authenticated
        )


motorista_admin_site = MotoristaAdminSite(name="motorista_admin")


class MotoristaInline(admin.StackedInline):
    model = Motorista
    form = MotoristaInlineForm
    can_delete = False
    verbose_name_plural = "Dados do motorista"
    extra = 0
    max_num = 1

    def get_min_num(self, request, obj=None, **kwargs):
        if obj and obj.role == Papel.MOTORISTA:
            return 1
        return 0


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ("celular", "nome", "role", "ativo")
    list_filter = ("role", "ativo")
    search_fields = ("celular", "nome")
    ordering = ("nome",)

    fieldsets = (
        (None, {"fields": ("celular", "password")}),
        ("Informações pessoais", {"fields": ("nome",)}),
        ("Permissões", {"fields": ("role", "ativo", "precisa_trocar_senha")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("celular", "nome", "role", "senha", "senha_confirmacao"),
            },
        ),
    )

    inlines = [MotoristaInline]

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.role == Papel.MOTORISTA:
            return [MotoristaInline]
        return []

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.role == Papel.MOTORISTA:
            if not hasattr(obj, "motorista"):
                Motorista.objects.create(
                    usuario=obj,
                    placa_caminhao="PENDENTE",
                )


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "placa_caminhao", "ativo")
    search_fields = ("usuario__nome", "placa_caminhao")
    list_filter = ("usuario__ativo",)
    raw_id_fields = ("usuario",)

    def ativo(self, obj):
        return obj.usuario.ativo

    ativo.boolean = True

    def has_delete_permission(self, request, obj=None):
        return False
