from decimal import Decimal
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: SecretStr

    jwt_secret: SecretStr
    jwt_algoritmo: str = "HS256"
    jwt_expira_minutos: int = Field(default=30, ge=5, le=120)
    jwt_emissor: str = "mufasa-api"
    jwt_publico: str = "mufasa-interface"

    ambiente: str = "desenvolvimento"
    forcar_https: bool = False
    hosts_permitidos: list[str] = ["localhost", "127.0.0.1", "testserver"]
    origens_cors: list[str] = []
    docs_habilitada: bool = True

    login_max_falhas: int = 5
    login_bloqueio_minutos: int = 15

    limite_req_minuto: int = 120
    limite_login_minuto: int = 10

    salario_minimo: Decimal | None = None

    apoio_chave: SecretStr | None = None

    nome_servico: str = "api"

    @field_validator("jwt_secret")
    @classmethod
    def _chave_forte(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET precisa de pelo menos 32 bytes aleatorios")
        return v

    @field_validator("jwt_algoritmo")
    @classmethod
    def _algoritmo_permitido(cls, v: str) -> str:
        if v not in ("HS256", "HS384", "HS512"):
            raise ValueError("JWT_ALGORITMO deve ser HS256, HS384 ou HS512")
        return v

    @property
    def em_producao(self) -> bool:
        return self.ambiente == "producao"


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
