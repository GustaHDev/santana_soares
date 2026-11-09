from django.db import transaction

from .models import Motorista, Papel, Usuario, normalizar_celular


@transaction.atomic
def criar_usuario_motorista(*, celular, nome, senha, placa_caminhao):
    celular = normalizar_celular(celular)
    usuario = Usuario.Objects.create_user(
        celular=celular,
        password=senha,
        nome=nome,
        role=Papel.MOTORISTA,
        precisa_trocar_senha=True,
    )
    motorista = Motorista.objects.create(
        usuario=usuario,
        placa_caminhao=placa_caminhao.upper().strip(),
    )
    return motorista


def trocar_senha(*, usuario, senha_atual, nova_senha):
    if not usuario.check_password(senha_atual):
        raise ValueError("Senha atual incorreta.")
    usuario.set_password(nova_senha)
    usuario.precisa_trocar_senha = False
    usuario.save(update_fields=["password", "precisa_trocar_senha"])
