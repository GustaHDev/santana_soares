from django.db import models

from core.mixins import TimestampMixin
from usuarios.models import Motorista, Usuario


class Fechamento(TimestampMixin):
    """Fase 2 — modelo criado agora apenas para suportar a FK em Viagem."""

    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        related_name="fechamentos",
        verbose_name="motorista",
    )
    mes_referencia = models.DateField(verbose_name="mês de referência")

    class Meta:
        verbose_name = "fechamento"
        verbose_name_plural = "fechamentos"
        constraints = [
            models.UniqueConstraint(
                fields=["motorista", "mes_referencia"],
                name="unique_fechamento_motorista_mes",
            ),
        ]

    def __str__(self):
        return f"Fechamento {self.motorista} — {self.mes_referencia:%m/%Y}"
