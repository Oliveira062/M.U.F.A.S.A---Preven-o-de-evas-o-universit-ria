import logging
import threading
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

CSP_DOCS = (
    "default-src 'none'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
)

TAMANHO_MAXIMO_CORPO = 64 * 1024
TAMANHO_MAXIMO_CARGA = 20 * 1024 * 1024 + 64 * 1024
CAMINHO_CARGA = "/api/v1/importacoes"

log_req = logging.getLogger("mufasa.requisicoes")
LENTA_MS = 2000


class CabecalhosSeguranca(BaseHTTPMiddleware):
    def __init__(self, app, hsts: bool):
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.id_requisicao = uuid.uuid4().hex[:12]

        tamanho = request.headers.get("content-length")
        limite = TAMANHO_MAXIMO_CARGA if request.url.path == CAMINHO_CARGA else TAMANHO_MAXIMO_CORPO
        if tamanho is None and "chunked" in request.headers.get("transfer-encoding", "").lower():
            return JSONResponse(
                {"titulo": "Tamanho obrigatório", "status": 411,
                 "detalhe": "Envie o cabeçalho Content-Length.", "requisicao": request.state.id_requisicao},
                status_code=411,
            )
        if tamanho is not None and (not tamanho.isdigit() or int(tamanho) > limite):
            return JSONResponse(
                {"titulo": "Conteúdo grande demais", "status": 413,
                 "detalhe": "O corpo da requisição excede o limite.", "requisicao": request.state.id_requisicao},
                status_code=413,
            )

        inicio = time.perf_counter()
        resposta = await call_next(request)
        duracao_ms = (time.perf_counter() - inicio) * 1000
        rota = getattr(request.scope.get("route"), "path", "rota-desconhecida")
        nivel = logging.WARNING if resposta.status_code >= 500 or duracao_ms > LENTA_MS else logging.INFO
        log_req.log(nivel, "req=%s %s %s -> %s em %.0f ms", request.state.id_requisicao, request.method, rota,
                    resposta.status_code, duracao_ms)

        caminho = request.url.path
        e_docs = caminho in ("/docs", "/redoc", "/openapi.json") or caminho.startswith("/docs/")
        resposta.headers["X-Request-ID"] = request.state.id_requisicao
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        resposta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resposta.headers["Content-Security-Policy"] = CSP_DOCS if e_docs else CSP_API
        resposta.headers["Cache-Control"] = "no-store"
        if self.hsts:
            resposta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if "server" in resposta.headers:
            del resposta.headers["server"]
        return resposta


class LimitadorJanela:

    def __init__(self):
        self._eventos: dict[str, deque] = defaultdict(deque)
        self._trava = threading.Lock()

    def permitir(self, chave: str, limite: int, janela: float = 60.0) -> tuple[bool, int]:
        agora = time.monotonic()
        with self._trava:
            fila = self._eventos[chave]
            while fila and agora - fila[0] > janela:
                fila.popleft()
            if len(fila) >= limite:
                espera = int(janela - (agora - fila[0])) + 1
                return False, espera
            fila.append(agora)
            return True, 0

    def limpar(self) -> None:
        with self._trava:
            self._eventos.clear()


limitador = LimitadorJanela()


def ip_do_cliente(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"
