from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import Motorista, Papel, Usuario, normalizar_celular


class UsuarioCreationForm(forms.ModelForm):
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
    )
    senha_confirmacao = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Usuario
        fields = ("celular", "nome", "role")

    def clean_celular(self):
        return normalizar_celular(self.cleaned_data["celular"])

    def clean(self):
        cleaned = super().clean()
        s1 = cleaned.get("senha")
        s2 = cleaned.get("senha_confirmacao")
        if s1 and s2 and s1 != s2:
            raise forms.ValidationError("As senhas não conferem.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["senha"])
        user.precisa_trocar_senha = True
        if commit:
            user.save()
        return user


class UsuarioChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Senha",
        help_text="Use o link abaixo para alterar a senha.",
    )

    class Meta:
        model = Usuario
        fields = ("celular", "nome", "role", "ativo", "precisa_trocar_senha", "password")

    def clean_celular(self):
        return normalizar_celular(self.cleaned_data["celular"])


class MotoristaInlineForm(forms.ModelForm):
    class Meta:
        model = Motorista
        fields = ("placa_caminhao",)


class TrocarSenhaForm(forms.Form):
    senha_atual = forms.CharField(
        label="Senha atual",
        widget=forms.PasswordInput,
    )
    nova_senha = forms.CharField(
        label="Nova senha",
        widget=forms.PasswordInput,
    )
    nova_senha_confirmacao = forms.CharField(
        label="Confirmar nova senha",
        widget=forms.PasswordInput,
    )

    def clean(self):
        cleaned = super().clean()
        s1 = cleaned.get("nova_senha")
        s2 = cleaned.get("nova_senha_confirmacao")
        if s1 and s2 and s1 != s2:
            raise forms.ValidationError("As senhas não conferem.")
        return cleaned
