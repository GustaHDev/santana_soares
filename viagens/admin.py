from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from usuarios.admin import motorista_admin_site
from usuarios.models import Papel

from .forms import ViagemAdminForm, ViagemMotoristaForm
from .models import StatusViagem, Viagem
from .services import criar_viagem, excluir_viagem, fechar_viagem


class ViagemAdminBase(admin.ModelAdmin):
    list_per_page = 25
    date_hierarchy = "data_saida"


@admin.register(Viagem)
class ViagemAdmin(ViagemAdminBase):
    form = ViagemAdminForm
    list_display = (
        "__str__",
        "motorista",
        "cliente_cidade",
        "origem",
        "data_saida",
        "data_chegada",
        "peso_ton",
        "status",
    )
    list_filter = ("status", "cliente_cidade__cidade__uf")
    search_fields = (
        "motorista__usuario__nome",
        "cliente_cidade__cliente__nome",
        "nota_fiscal",
    )
    raw_id_fields = ("motorista", "cliente_cidade", "origem", "fechada_por")

    readonly_fields = (
        "status",
        "fechada_em",
        "fechada_por",
        "fechamento",
        "valor_total_display",
        "valor_motorista_display",
        "margem_bruta_display",
        "km_rodado_display",
    )

    fieldsets = (
        (
            "Dados da viagem (motorista)",
            {
                "fields": (
                    "motorista",
                    "cliente_cidade",
                    "origem",
                    "data_saida",
                    "nota_fiscal",
                    "peso_ton",
                    "km_inicial",
                    "data_chegada",
                    "km_final",
                ),
            },
        ),
        (
            "Dados do admin",
            {
                "fields": (
                    "tonelada_cliente",
                    "tonelada_motorista",
                    "cte",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "fechada_em",
                    "fechada_por",
                    "fechamento",
                ),
            },
        ),
        (
            "Valores calculados",
            {
                "classes": ("collapse",),
                "fields": (
                    "km_rodado_display",
                    "valor_total_display",
                    "valor_motorista_display",
                    "margem_bruta_display",
                ),
            },
        ),
    )

    actions = ["action_fechar_viagens"]

    def _formatar_decimal(self, valor):
        if valor is None:
            return "—"
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def valor_total_display(self, obj):
        return self._formatar_decimal(obj.valor_total)

    valor_total_display.short_description = "Valor total"

    def valor_motorista_display(self, obj):
        return self._formatar_decimal(obj.valor_motorista)

    valor_motorista_display.short_description = "Valor motorista"

    def margem_bruta_display(self, obj):
        return self._formatar_decimal(obj.margem_bruta)

    margem_bruta_display.short_description = "Margem bruta"

    def km_rodado_display(self, obj):
        km = obj.km_rodado
        return f"{km} km" if km is not None else "—"

    km_rodado_display.short_description = "Km rodado"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.tonelada_cliente = obj.cliente_cidade.preco_tonelada
        super().save_model(request, obj, form, change)

        if change and obj.tonelada_motorista and obj.tonelada_cliente:
            if obj.tonelada_motorista >= obj.tonelada_cliente:
                messages.warning(
                    request,
                    "Atenção: tonelada do motorista é maior ou igual à do cliente. "
                    "Esta viagem terá margem zero ou negativa.",
                )

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == StatusViagem.FECHADA:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        try:
            excluir_viagem(viagem=obj, usuario=request.user)
        except ValidationError as e:
            messages.error(request, str(e.message))

    @admin.action(description="Fechar viagens selecionadas")
    def action_fechar_viagens(self, request, queryset):
        fechadas = 0
        erros = 0
        for viagem in queryset.filter(status=StatusViagem.ABERTA):
            try:
                fechar_viagem(viagem=viagem, usuario=request.user)
                fechadas += 1
            except ValidationError as e:
                erros += 1
                msg_list = e.messages if hasattr(e, "messages") else [str(e)]
                messages.error(
                    request,
                    f"Viagem #{viagem.pk}: {'; '.join(msg_list)}",
                )
        if fechadas:
            messages.success(request, f"{fechadas} viagem(ns) fechada(s).")
        if erros:
            messages.warning(request, f"{erros} viagem(ns) não puderam ser fechadas.")


class ViagemMotoristaAdmin(ViagemAdminBase):
    form = ViagemMotoristaForm
    list_display = (
        "__str__",
        "cliente_cidade",
        "origem",
        "data_saida",
        "data_chegada",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("cliente_cidade__cliente__nome", "nota_fiscal")

    fields = (
        "cliente_cidade",
        "origem",
        "data_saida",
        "nota_fiscal",
        "peso_ton",
        "km_inicial",
        "data_chegada",
        "km_final",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request.user, "motorista"):
            return qs.filter(motorista=request.user.motorista)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.motorista = request.user.motorista
            obj.tonelada_cliente = obj.cliente_cidade.preco_tonelada
            obj.status = StatusViagem.ABERTA
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != StatusViagem.ABERTA:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status != StatusViagem.ABERTA:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        try:
            excluir_viagem(viagem=obj, usuario=request.user)
        except ValidationError as e:
            messages.error(request, str(e.message))


motorista_admin_site.register(Viagem, ViagemMotoristaAdmin)
