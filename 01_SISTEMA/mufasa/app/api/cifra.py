import json

from cryptography.fernet import Fernet, InvalidToken

from app.config import obter_configuracao


class ChaveIndisponivel(Exception):
    pass


def _fernet(chave: str | None = None) -> Fernet:
    if chave is None:
        configurada = obter_configuracao().apoio_chave
        if configurada is None:
            raise ChaveIndisponivel("APOIO_CHAVE nao configurada")
        chave = configurada.get_secret_value()
    try:
        return Fernet(chave.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ChaveIndisponivel("APOIO_CHAVE invalida") from exc


def cifrar(dados: dict, chave: str | None = None) -> str:
    return _fernet(chave).encrypt(json.dumps(dados, ensure_ascii=False).encode("utf-8")).decode("ascii")


def decifrar(token: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(token.encode("ascii")))
    except InvalidToken as exc:
        raise ChaveIndisponivel("dado de apoio nao confere com a chave") from exc
