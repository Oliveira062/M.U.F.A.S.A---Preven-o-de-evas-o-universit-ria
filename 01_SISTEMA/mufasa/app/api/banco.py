from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.config import obter_configuracao

_engine: Engine | None = None


def obter_engine() -> Engine:
    global _engine
    if _engine is None:
        cfg = obter_configuracao()
        _engine = create_engine(
            cfg.database_url.get_secret_value(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            echo=False,
            hide_parameters=True,
        )
    return _engine


def obter_conexao() -> Iterator[Connection]:
    with obter_engine().connect() as conexao:
        yield conexao
