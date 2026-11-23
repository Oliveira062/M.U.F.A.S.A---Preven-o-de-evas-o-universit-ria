from fastapi import Request
from sqlalchemy.engine import Connection

from app.api import auditoria
from app.api.auth import Usuario
import json

from app.api.consultas import ALERTA_ABERTO_DO_ALUNO, ALUNO_DAS_TURMAS_DO_DOCENTE, ALUNO_DO_CURSO
from app.api.erros import MSG_ACESSO_NEGADO, erro_http

ALUNO = "ALUNO"
DOCENTE = "DOCENTE"
COORDENACAO = "COORDENACAO"
NUCLEO_APOIO = "NUCLEO_APOIO"
FINANCEIRO = "FINANCEIRO"
DIRECAO = "DIRECAO"
ADMIN = "ADMIN"
ENCARREGADO_DADOS = "ENCARREGADO_DADOS"

PERFIS = (ALUNO, DOCENTE, COORDENACAO, NUCLEO_APOIO, FINANCEIRO, DIRECAO, ADMIN, ENCARREGADO_DADOS)

LEITURA_INDIVIDUAL = (ALUNO, DOCENTE, COORDENACAO, NUCLEO_APOIO, FINANCEIRO)

NIVEIS_DE_ALERTA = ("ALTO", "CRITICO")

FATORES_SOCIOECONOMICOS = {"financeiro", "trabalho", "deslocamento", "moradia", "dependentes"}
FATORES_SAUDE = {"saude_mental", "saude_fisica"}
ROTULO_ENCAMINHADO = "fator encaminhado ao núcleo de apoio"


def _no_escopo(conexao: Connection, usuario: Usuario, id_aluno: str) -> bool:
    if usuario.perfil == ALUNO:
        return usuario.id_aluno is not None and usuario.id_aluno == id_aluno

    if usuario.perfil == DOCENTE:
        return usuario.id_professor is not None and conexao.execute(
            ALUNO_DAS_TURMAS_DO_DOCENTE, {"id_aluno": id_aluno, "id_professor": usuario.id_professor}
        ).first() is not None

    if usuario.perfil == COORDENACAO:
        return usuario.id_curso is not None and conexao.execute(
            ALUNO_DO_CURSO, {"id_aluno": id_aluno, "id_curso": usuario.id_curso}
        ).first() is not None

    if usuario.perfil in (NUCLEO_APOIO, FINANCEIRO):
        alerta = conexao.execute(ALERTA_ABERTO_DO_ALUNO, {"id_aluno": id_aluno}).mappings().first()
        if alerta is None:
            return False
        if usuario.perfil == NUCLEO_APOIO:
            return alerta["id_responsavel"] == usuario.id_usuario
        return "financeiro" in fatores_da_linha(alerta["fatores_principais"])

    return False


def fatores_da_linha(valor) -> list[str]:
    if not valor:
        return []
    return json.loads(valor) if isinstance(valor, str) else list(valor)


def verificar_escopo_aluno(request: Request, conexao: Connection, usuario: Usuario,
                           id_aluno: str, operacao: str) -> None:
    if usuario.perfil not in LEITURA_INDIVIDUAL or not _no_escopo(conexao, usuario, id_aluno):
        auditoria.registrar(request, operacao, "NEGADO", usuario=usuario, id_aluno_alvo=id_aluno)
        raise erro_http(403, MSG_ACESSO_NEGADO)
    auditoria.registrar(request, operacao, "PERMITIDO", usuario=usuario, id_aluno_alvo=id_aluno)


def fator_visivel(perfil: str, fator: str) -> bool:
    if perfil in (ALUNO, NUCLEO_APOIO):
        return True
    if fator in FATORES_SAUDE:
        return False
    if perfil == DOCENTE and fator in FATORES_SOCIOECONOMICOS:
        return False
    return True


def valor_do_fator_visivel(perfil: str, fator: str) -> bool:
    if perfil in (ALUNO, NUCLEO_APOIO):
        return True
    if perfil == COORDENACAO and fator in FATORES_SOCIOECONOMICOS:
        return False
    return fator_visivel(perfil, fator)


def faixa_qualitativa(risco: float) -> str:
    if risco <= 33:
        return "baixa"
    if risco <= 66:
        return "média"
    return "alta"
