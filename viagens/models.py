from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from cadastros.models import Cidade, ClienteCidade
from core.mixins import TimestampMixin
from usuarios.models import Motorista, Usuario


class StatusViagem(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    FECHADA = "fechada", "Fechada"


class ViagemQuerySet(models.QuerySet):
    def abertas(self):
        return self.filter(status=StatusViagem.ABERTA)

    def fechadas(self):
        return self.filter(status=StatusViagem.FECHADA)

    def do_motorista(self, motorista):
        return self.filter(motorista=motorista)

    def do_mes(self, ano, mes):
        return self.filter(data_chegada__year=ano, data_chegada__month=mes)


class Viagem(TimestampMixin):
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        related_name="viagens",
        verbose_name="motorista",
    )
    cliente_cidade = models.ForeignKey(
        ClienteCidade,
        on_delete=models.PROTECT,
        related_name="viagens",
        verbose_name="cliente / destino",
    )
    origem = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        related_name="viagens_origem",
        verbose_name="origem",
    )
    data_saida = models.DateField(verbose_name="data de saída")
    nota_fiscal = models.CharField(max_length=50, verbose_name="nota fiscal")
    peso_ton = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="peso (ton)",
    )
    km_inicial = models.PositiveIntegerField(verbose_name="km inicial")

    data_chegada = models.DateField(
        null=True,
        blank=True,
        verbose_name="data de chegada",
    )
    km_final = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="km final",
    )

    tonelada_cliente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="tonelada cliente (R$)",
    )
    tonelada_motorista = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="tonelada motorista (R$)",
    )
    cte = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="CT-e",
    )

    status = models.CharField(
        max_length=10,
        choices=StatusViagem.choices,
        default=StatusViagem.ABERTA,
        verbose_name="status",
    )
    fechada_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="fechada em",
    )
    fechada_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="viagens_fechadas",
        verbose_name="fechada por",
    )
    fechamento = models.ForeignKey(
        "financeiro.Fechamento",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="viagens",
        verbose_name="fechamento mensal",
    )

    history = HistoricalRecords()

    objects = ViagemQuerySet.as_manager()

    class Meta:
        verbose_name = "viagem"
        verbose_name_plural = "viagens"
        ordering = ["-data_saida", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_ton__gt=0),
                name="viagem_peso_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(tonelada_cliente__gt=0),
                name="viagem_tonelada_cliente_positiva",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(km_final__isnull=True)
                    | models.Q(km_final__gte=models.F("km_inicial"))
                ),
                name="viagem_km_final_gte_inicial",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(data_chegada__isnull=True)
                    | models.Q(data_chegada__gte=models.F("data_saida"))
                ),
                name="viagem_chegada_gte_saida",
            ),
        ]

    def __str__(self):
        return (
            f"Viagem #{self.pk} — {self.motorista.usuario.nome} "
            f"({self.data_saida})"
        )

    @property
    def km_rodado(self):
        if self.km_final is not None and self.km_inicial is not None:
            return self.km_final - self.km_inicial
        return None

    @property
    def valor_total(self):
        if self.peso_ton and self.tonelada_cliente:
            return self.peso_ton * self.tonelada_cliente
        return None

    @property
    def valor_motorista(self):
        if self.peso_ton and self.tonelada_motorista:
            return self.peso_ton * self.tonelada_motorista
        return None

    @property
    def margem_bruta(self):
        vt = self.valor_total
        vm = self.valor_motorista
        if vt is not None and vm is not None:
            return vt - vm
        return None

    @property
    def is_aberta(self):
        return self.status == StatusViagem.ABERTA

    @property
    def is_fechada(self):
        return self.status == StatusViagem.FECHADA

    @property
    def cliente_faz_cte(self):
        return self.cliente_cidade.cliente.faz_cte
