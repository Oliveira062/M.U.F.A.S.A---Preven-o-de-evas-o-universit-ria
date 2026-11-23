import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("mufasa.erros")

TITULOS = {
    400: "Requisição inválida",
    401: "Autenticação necessária",
    403: "Permissão insuficiente",
    404: "Recurso não encontrado",
    405: "Método não permitido",
    409: "Conflito",
    413: "Conteúdo grande demais",
    422: "Dados inválidos",
    423: "Acesso bloqueado temporariamente",
    429: "Muitas requisições",
    500: "Erro interno",
}

MSG_ACESSO_NEGADO = "Você não tem permissão para acessar os dados deste aluno, ou ele não existe."


MENSAGENS_VALIDACAO = {
    "missing": "Campo obrigatório.",
    "extra_forbidden": "Campo não permitido.",
    "string_too_short": "Texto curto demais.",
    "string_too_long": "Texto longo demais.",
    "string_pattern_mismatch": "Formato inválido.",
    "string_type": "Precisa ser texto.",
    "int_parsing": "Precisa ser um número inteiro.",
    "int_type": "Precisa ser um número inteiro.",
    "greater_than_equal": "Valor abaixo do mínimo permitido.",
    "less_than_equal": "Valor acima do máximo permitido.",
    "enum": "Valor fora da lista permitida.",
    "bool_parsing": "Precisa ser verdadeiro ou falso.",
    "json_invalid": "JSON inválido.",
}


def _id_requisicao(request: Request) -> str:
    return getattr(request.state, "id_requisicao", "-")


def resposta_erro(request: Request, status: int, detalhe: str, extra: dict | None = None,
                  cabecalhos: dict | None = None) -> JSONResponse:
    corpo = {
        "titulo": TITULOS.get(status, "Erro"),
        "status": status,
        "detalhe": detalhe,
        "requisicao": _id_requisicao(request),
    }
    if extra:
        corpo.update(extra)
    cabecalhos = {"X-Request-ID": corpo["requisicao"], "Cache-Control": "no-store",
                  "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'",
                  **(cabecalhos or {})}
    return JSONResponse(corpo, status_code=status, headers=cabecalhos)


def registrar_tratadores(app: FastAPI, registrar_erro=None) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        detalhe = exc.detail if isinstance(exc.detail, str) else TITULOS.get(exc.status_code, "Erro")
        return resposta_erro(request, exc.status_code, detalhe, cabecalhos=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        campos = [
            {"campo": ".".join(str(p) for p in erro.get("loc", ()) if p != "body"),
             "mensagem": MENSAGENS_VALIDACAO.get(erro.get("type"), "Valor inválido.")}
            for erro in exc.errors()
        ]
        return resposta_erro(request, 422, "Um ou mais campos estão inválidos.", {"campos": campos})

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception):
        log.exception("Erro nao tratado: req=%s %s %s", _id_requisicao(request), request.method,
                      getattr(request.scope.get("route"), "path", "rota-desconhecida"))
        if registrar_erro is not None:
            try:
                registrar_erro(type(exc).__name__, _id_requisicao(request))
            except Exception:
                log.exception("Falha ao gravar o registro tecnico")
        return resposta_erro(request, 500, "Ocorreu um erro inesperado. Informe o código da requisição ao suporte.")


def erro_http(status: int, detalhe: str, cabecalhos: dict | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail=detalhe, headers=cabecalhos)
