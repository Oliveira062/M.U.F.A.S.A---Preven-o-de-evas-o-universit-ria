from app.chatbot.banco_chat import obter_engine_chat
from app.chatbot.rotas_chat import router_chat
from app.fabrica import criar_servico

from app.registro import configurar_registro

configurar_registro("chat")


def criar_app():
    return criar_servico("chat", "MUFASA Chat", (router_chat,), obter_engine_chat, sinal_de_vida=True)


app = criar_app()
