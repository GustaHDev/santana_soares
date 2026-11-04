from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import StatusViagem, Viagem


@transaction.atomic
def criar_viagem(
    *,
    motorista,
    cliente_cidade,
    origem,
    data_saida,
    nota_fiscal,
    peso_ton,
    km_inicial,
    data_chegada=None,
    km_final=None,
):
    if not cliente_cidade.ativo:
        raise ValidationError("Este cliente/cidade não está ativo.")

    viagem = Viagem(
        motorista=motorista,
        cliente_cidade=cliente_cidade,
        origem=origem,
        data_saida=data_saida,
        nota_fiscal=nota_fiscal,
        peso_ton=peso_ton,
        km_inicial=km_inicial,
        data_chegada=data_chegada,
        km_final=km_final,
        tonelada_cliente=cliente_cidade.preco_tonelada,
        status=StatusViagem.ABERTA,
    )
    viagem.full_clean()
    viagem.save()
    return viagem


def sugerir_tonelada_motorista(cliente_cidade):
    ultima = (
        Viagem.objects.filter(
            cliente_cidade=cliente_cidade,
            tonelada_motorista__isnull=False,
        )
        .order_by("-id")
        .values_list("tonelada_motorista", flat=True)
        .first()
    )
    return ultima


@transaction.atomic
def fechar_viagem(*, viagem, usuario):
    erros = []

    if viagem.status == StatusViagem.FECHADA:
        raise ValidationError("Esta viagem já está fechada.")

    if not viagem.data_chegada:
        erros.append("Data de chegada é obrigatória para fechar a viagem.")
    if viagem.km_final is None:
        erros.append("Km final é obrigatório para fechar a viagem.")
    if not viagem.tonelada_cliente:
        erros.append("Tonelada cliente é obrigatória para fechar a viagem.")
    if not viagem.tonelada_motorista:
        erros.append("Tonelada motorista é obrigatória para fechar a viagem.")
    if viagem.cliente_faz_cte and not viagem.cte:
        erros.append("CT-e é obrigatório para este cliente.")

    if erros:
        raise ValidationError(erros)

    viagem.status = StatusViagem.FECHADA
    viagem.fechada_em = timezone.now()
    viagem.fechada_por = usuario
    viagem.save()
    return viagem


def excluir_viagem(*, viagem, usuario):
    if viagem.status != StatusViagem.ABERTA:
        raise ValidationError("Só é possível excluir viagens abertas.")
    viagem.delete()
