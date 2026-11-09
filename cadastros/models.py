from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from core.mixins import AtivoMixin, TimestampMixin

UFS_BRASIL = [
    ("AC", "AC"), ("AL", "AL"), ("AP", "AP"), ("AM", "AM"), ("BA", "BA"),
    ("CE", "CE"), ("DF", "DF"), ("ES", "ES"), ("GO", "GO"), ("MA", "MA"),
    ("MT", "MT"), ("MS", "MS"), ("MG", "MG"), ("PA", "PA"), ("PB", "PB"),
    ("PR", "PR"), ("PE", "PE"), ("PI", "PI"), ("RJ", "RJ"), ("RN", "RN"),
    ("RS", "RS"), ("RO", "RO"), ("RR", "RR"), ("SC", "SC"), ("SP", "SP"),
    ("SE", "SE"), ("TO", "TO"),
]


class CidadeQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Cidade(TimestampMixin, AtivoMixin):
    nome = models.CharField(
        max_length=120, 
        verbose_name="nome"
    )

    uf = models.CharField(
        max_length=2, 
        choices=UFS_BRASIL, 
        verbose_name="UF"
    )

    objects = CidadeQuerySet.as_manager()

    class Meta:
        verbose_name = "cidade"
        verbose_name_plural = "cidades"
        ordering = ["nome", "uf"]
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "uf"],
                name="unique_cidade_nome_uf",
            ),
        ]

    def __str__(self):
        return f"{self.nome}/{self.uf}"


class ClienteQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class Cliente(TimestampMixin, AtivoMixin):
    nome = models.CharField(
        max_length=200, 
        verbose_name="nome"
    )

    faz_cte = models.BooleanField(
        default=False, 
        verbose_name="faz CT-e"
    )

    objects = ClienteQuerySet.as_manager()

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ClienteCidadeQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True, cliente__ativo=True, cidade__ativo=True)


class ClienteCidade(TimestampMixin, AtivoMixin):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="cidades",
        verbose_name="cliente",
    )

    cidade = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        related_name="clientes",
        verbose_name="cidade",
    )
    
    preco_tonelada = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.01)],
        verbose_name="preço por tonelada (R$)",
    )

    history = HistoricalRecords()

    objects = ClienteCidadeQuerySet.as_manager()

    class Meta:
        verbose_name = "cliente-cidade"
        verbose_name_plural = "clientes-cidades"
        ordering = ["cliente__nome", "cidade__nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "cidade"],
                name="unique_cliente_cidade",
            ),
        ]

    def __str__(self):
        return f"{self.cliente.nome} — {self.cidade}"
