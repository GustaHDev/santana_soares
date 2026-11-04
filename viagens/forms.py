from django import forms

from cadastros.models import ClienteCidade
from .models import Viagem


class ViagemMotoristaForm(forms.ModelForm):
    cliente_cidade = forms.ModelChoiceField(
        queryset=ClienteCidade.objects.ativos().select_related("cliente", "cidade"),
        label="Cliente / Destino",
    )

    class Meta:
        model = Viagem
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["origem"].queryset = (
            self.fields["origem"].queryset.filter(ativo=True)
        )


class ViagemAdminForm(forms.ModelForm):
    class Meta:
        model = Viagem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")
        if instance and not instance.cliente_faz_cte:
            if "cte" in self.fields:
                self.fields["cte"].widget = forms.HiddenInput()
                self.fields["cte"].required = False

        if instance and instance.cliente_cidade_id:
            from viagens.services import sugerir_tonelada_motorista

            sugestao = sugerir_tonelada_motorista(instance.cliente_cidade)
            if sugestao and not instance.tonelada_motorista:
                self.fields["tonelada_motorista"].initial = sugestao
                self.fields["tonelada_motorista"].help_text = (
                    f"Sugestão da última viagem: R$ {sugestao}"
                )
