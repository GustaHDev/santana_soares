import re

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from core.mixins import AtivoMixin, TimestampMixin


class Papel(models.TextChoices):
    ADMIN = "admin", "Administrador"
    MOTORISTA = "motorista", "Motorista"


def validar_celular(valor):
    digitos = normalizar_celular(valor)
    if len(digitos) < 10 or len(digitos) > 11:
        raise ValidationError("Celular deve ter 10 ou 11 dígitos (com DDD).")


def normalizar_celular(valor):
    return re.sub(r"\D", "", valor)


class UsuarioManager(BaseUserManager):
    def create_user(self, celular, password=None, **extra_fields):
        if not celular:
            raise ValueError("O campo celular é obrigatório.")
        celular = normalizar_celular(celular)
        user = self.model(celular=celular, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, celular, password=None, **extra_fields):
        extra_fields.setdefault("role", Papel.ADMIN)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("precisa_trocar_senha", False)
        return self.create_user(celular, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin, TimestampMixin):
    celular = models.CharField(
        max_length=11,
        unique=True,
        verbose_name="celular",
        validators=[validar_celular],
        help_text="Somente dígitos, com DDD.",
    )

    nome = models.CharField(
        max_length=150, 
        verbose_name="nome"
    )

    role = models.CharField(
        max_length=10,
        choices=Papel.choices,
        default=Papel.MOTORISTA,
        verbose_name="papel",
    )

    ativo = models.BooleanField(
        default=True, 
        verbose_name="ativo"
    )

    precisa_trocar_senha = models.BooleanField(
        default=True,
        verbose_name="precisa trocar senha",
    )

    is_staff = models.BooleanField(
        default=True,
        verbose_name="acesso ao painel",
    )

    Objects = UsuarioManager()

    USERNAME_FIELD = "celular"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def is_active(self):
        return self.ativo

    @property
    def is_admin(self):
        return self.role == Papel.ADMIN

    @property
    def is_motorista(self):
        return self.role == Papel.MOTORISTA

    def clean(self):
        super().clean()
        if self.celular:
            self.celular = normalizar_celular(self.celular)

    def save(self, *args, **kwargs):
        if self.celular:
            self.celular = normalizar_celular(self.celular)
        super().save(*args, **kwargs)


class Motorista(TimestampMixin):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.PROTECT,
        related_name="motorista",
        verbose_name="usuário",
    )
    placa_caminhao = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="placa do caminhão",
    )

    class Meta:
        verbose_name = "motorista"
        verbose_name_plural = "motoristas"
        ordering = ["usuario__nome"]

    def __str__(self):
        return f"{self.usuario.nome} ({self.placa_caminhao})"

    @property
    def nome(self):
        return self.usuario.nome

    @property
    def celular(self):
        return self.usuario.celular

    @property
    def ativo(self):
        return self.usuario.ativo
