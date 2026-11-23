import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from scripts._ambiente import RAIZ, carregar_env

PARTES = {
    "api": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    "chat": [sys.executable, "-m", "uvicorn", "app.main_chat:app", "--host", "127.0.0.1", "--port", "8001"],
    "calculo": [sys.executable, "-m", "app.servico_calculo"],
    "painel": [sys.executable, "-m", "streamlit", "run", "app.py"],
}
PASTA = {"painel": RAIZ / "painel"}
OBRIGATORIAS = {"api": ["DATABASE_URL", "JWT_SECRET"], "chat": ["CHAT_DATABASE_URL", "JWT_SECRET"],
                "calculo": ["CALCULO_DATABASE_URL"], "painel": []}


class Parte:
    def __init__(self, nome: str, logs: Path):
        self.nome, self.logs = nome, logs
        self.proc: subprocess.Popen | None = None
        self.espera = 2.0
        self.proxima_tentativa = 0.0
        self.iniciada_em = 0.0
        self.reinicios = 0

    def iniciar(self):
        saida = open(self.logs / f"{self.nome}.console.log", "a", encoding="utf-8")
        saida.write(f"\n===== inicio {time.strftime('%d/%m/%Y %H:%M:%S')} =====\n")
        saida.flush()
        self.proc = subprocess.Popen(PARTES[self.nome], cwd=PASTA.get(self.nome, RAIZ), stdout=saida,
                                     stderr=subprocess.STDOUT, env=os.environ.copy())
        self.iniciada_em = time.monotonic()
        print(f"[{time.strftime('%H:%M:%S')}] {self.nome:8} iniciado (pid {self.proc.pid})")

    def conferir(self):
        if self.proc is None or self.proc.poll() is None:
            if self.proc and time.monotonic() - self.iniciada_em > 120:
                self.espera = 2.0
            return
        agora = time.monotonic()
        if self.proxima_tentativa == 0.0:
            codigo = self.proc.returncode
            print(f"[{time.strftime('%H:%M:%S')}] {self.nome:8} PAROU (codigo {codigo}); nova tentativa em "
                  f"{self.espera:.0f} s. Detalhes: logs/{self.nome}.console.log")
            self.proxima_tentativa = agora + self.espera
            self.espera = min(60.0, self.espera * 2)
        elif agora >= self.proxima_tentativa:
            self.proxima_tentativa = 0.0
            self.reinicios += 1
            self.iniciar()

    def parar(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def main() -> int:
    carregar_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so", help="lista separada por virgula: api,chat,calculo,painel")
    ap.add_argument("--sem-chat", action="store_true")
    args = ap.parse_args()
    nomes = args.so.split(",") if args.so else list(PARTES)
    if args.sem_chat and "chat" in nomes:
        nomes.remove("chat")
    desconhecidas = set(nomes) - set(PARTES)
    if desconhecidas:
        print(f"Partes desconhecidas: {', '.join(desconhecidas)}", file=sys.stderr)
        return 2
    faltando = sorted({v for n in nomes for v in OBRIGATORIAS[n] if not os.environ.get(v)})
    if faltando:
        print("Faltam variaveis no .env: " + ", ".join(faltando) + ". Veja .env.example.", file=sys.stderr)
        return 2
    os.environ.setdefault("MUFASA_API_URL", "http://127.0.0.1:8000")
    os.environ.setdefault("MUFASA_CHAT_URL", "http://127.0.0.1:8001")
    logs = Path(os.environ.get("MUFASA_LOG_DIR", RAIZ / "logs"))
    logs.mkdir(parents=True, exist_ok=True)

    partes = [Parte(n, logs) for n in nomes]
    for p in partes:
        p.iniciar()
    if "painel" in nomes:
        print("\nPainel: http://127.0.0.1:8501   (Ctrl+C para encerrar)")
        print("Conferir tudo: python -m scripts.diagnostico\n")
    try:
        while True:
            for p in partes:
                p.conferir()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        for p in partes:
            p.parar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
