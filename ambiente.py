"""Carrega o .env pro os.environ. Sem lib externa, sem efeito colateral
alem disso -- usado tanto pelo entrypoint (tarefas.py) quanto por scripts
de diagnostico standalone (testar_firebird.py) que nao podem importar
tarefas.py (isso regeneraria imagens e carregaria a lib de automacao).
"""
import os

CAMINHO = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def carregar_env(caminho: str = CAMINHO) -> None:
    if not os.path.exists(caminho):
        return
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            os.environ.setdefault(chave.strip(), valor.strip())
