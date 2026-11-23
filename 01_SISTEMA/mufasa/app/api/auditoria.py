import logging
from datetime import datetime, timezone

from fastapi import Request

from app.api import banco
from app.api.consultas import REGISTRAR_AUDITORIA
from app.api.seguranca import ip_do_cliente

log = logging.getLogger("mufasa.auditoria")


def registrar(request: Request, operacao: str, resultado: str, *, usuario=None,
              id_aluno_alvo: str | None = None) -> None:
    valores = {
        "momento": datetime.now(timezone.utc),
        "id_requisicao": getattr(request.state, "id_requisicao", None),
        "id_usuario": getattr(usuario, "id_usuario", None),
        "perfil": getattr(usuario, "perfil", None),
        "operacao": operacao,
        "recurso": request.url.path[:200],
        "id_aluno_alvo": id_aluno_alvo,
        "resultado": resultado,
        "origem": ip_do_cliente(request)[:45],
    }
    try:
        with banco.obter_engine().begin() as conexao:
            conexao.execute(REGISTRAR_AUDITORIA, valores)
    except Exception:
        log.exception("Falha ao gravar auditoria da requisicao %s", valores["id_requisicao"])
        raise
