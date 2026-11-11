"""O botao LIGA. So monta o processo e manda rodar. Nao decide nada.

Uso:
    python tarefas.py              # roda as duas fases, em sequencia
    python tarefas.py gerar        # so Fase 1 (Geracao de Lotes)
    python tarefas.py transmitir   # so Fase 2 (Transmissao dos Lotes)

Senhas vem do .env (nao versionado). Formato do .env:
    SIS_USUARIO=fulano
    SIS_SENHA=segredo
"""
import logging
import os
import subprocess
import sys
from datetime import date

import gerar_imagens
from ambiente import carregar_env
from configuracoes import CONFIG


def _configurar_logging() -> None:
    dir_logs = CONFIG["caminhos"]["logs"]
    os.makedirs(dir_logs, exist_ok=True)
    caminho = os.path.join(dir_logs, f"robo_{date.today():%Y%m%d}.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(caminho, encoding="utf-8")],
    )


def main() -> int:
    _configurar_logging()
    carregar_env()

    try:
        gerar_imagens.gerar()   # antes de importar a lib de automacao
        print('Imagens geradas')
        
        from processo import Processo

        argv = sys.argv[1:]
        # Se o processo ganhar flags proprias (ex: forcar um passo que so
        # roda 1x/dia), siga este padrao: extrai a flag de argv, passa como
        # parametro nomeado pra executar() -- nao deixe Processo ler sys.argv.
        fluxo = argv[0] if argv else None

        credenciais = {
            "usuario": os.environ.get("SIS_USUARIO", ""),
            "senha": os.environ.get("SIS_SENHA", ""),
        }

        Processo(CONFIG, credenciais).executar(fluxo=fluxo)
        return 0
    except Exception:
        logging.exception("Robo parou com erro")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ctrl+C nao herda de Exception -- o except de main() nao pega.
        # Pausa so aqui (nunca nos outros caminhos de saida) pra nao travar
        # uma execucao agendada esperando tecla de ninguem.
        logging.warning("Interrompido pelo usuario (Ctrl+C)")
        subprocess.run(["pause"], shell=True)
        sys.exit(1)
