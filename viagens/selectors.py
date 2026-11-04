from django.db.models import F, ExpressionWrapper, DecimalField

from .models import Viagem


def listar_viagens_admin(*, filters=None):
    qs = Viagem.objects.select_related(
        "motorista__usuario",
        "cliente_cidade__cliente",
        "cliente_cidade__cidade",
        "origem",
        "fechada_por",
    )
    if filters:
        if filters.get("motorista"):
            qs = qs.filter(motorista=filters["motorista"])
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("data_saida_de"):
            qs = qs.filter(data_saida__gte=filters["data_saida_de"])
        if filters.get("data_saida_ate"):
            qs = qs.filter(data_saida__lte=filters["data_saida_ate"])
        if filters.get("cliente"):
            qs = qs.filter(cliente_cidade__cliente=filters["cliente"])
    return qs


def listar_viagens_motorista(*, motorista):
    return (
        Viagem.objects.filter(motorista=motorista)
        .select_related(
            "cliente_cidade__cliente",
            "cliente_cidade__cidade",
            "origem",
        )
    )


def viagens_do_mes(*, motorista, ano, mes):
    return (
        Viagem.objects.filter(
            motorista=motorista,
            status="fechada",
            data_chegada__year=ano,
            data_chegada__month=mes,
        )
        .select_related(
            "cliente_cidade__cliente",
            "cliente_cidade__cidade",
            "origem",
        )
        .annotate(
            _valor_motorista=ExpressionWrapper(
                F("peso_ton") * F("tonelada_motorista"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
    )
