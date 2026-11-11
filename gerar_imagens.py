"""Gera paginas/imagens_geradas.py com uma constante IMG_<NOME> por
arquivo .png em paginas/imagens/<fase>/ -- assim o editor tem autocomplete
de verdade (sao atributos reais de um modulo), sem manter nome de arquivo
na mao em tela.py.

As imagens ficam separadas por fase (paginas/imagens/gerar/,
paginas/imagens/transmitir/) so pra nao misturar os prints dos dois
fluxos numa pasta so -- a constante gerada e so o nome do arquivo, sem a
fase (IMG_MENU, nao IMG_TRANSMITIR_MENU), entao dois prints com o MESMO
nome em fases diferentes colidiriam; o segundo e ignorado com aviso.

Chamado automaticamente por tarefas.py ANTES de importar a lib de
automacao, mas pode ser rodado direto tambem:

    python gerar_imagens.py
"""
import logging
import os
import re

from configuracoes import CONFIG

logger = logging.getLogger(__name__)

CAMINHO_GERADO = os.path.join(os.path.dirname(__file__), "paginas", "imagens_geradas.py")


def _listar_imagens() -> list:
    dir_imagens = CONFIG["caminhos"]["imagens"]
    if not os.path.isdir(dir_imagens):
        return []
    arquivos = []
    for fase in sorted(os.listdir(dir_imagens)):
        dir_fase = os.path.join(dir_imagens, fase)
        if not os.path.isdir(dir_fase):
            continue
        for nome in sorted(os.listdir(dir_fase)):
            if nome.lower().endswith(".png"):
                # "/" (nao os.path.join) -- vira string literal no .py gerado,
                # e "\" dentro de uma string gera escape invalido no Windows.
                # os.path.join aceita "/" de boa na hora de montar o caminho real.
                arquivos.append(f"{fase}/{nome}")
    return sorted(arquivos)


def _arquivos_no_gerado() -> "list | None":

    if not os.path.exists(CAMINHO_GERADO):
        return None
    with open(CAMINHO_GERADO, encoding="utf-8") as f:
        conteudo = f.read()
    return sorted(re.findall(r'^IMG_\w+ = "(.+\.png)"$', conteudo, flags=re.MULTILINE))



def _escrever(arquivos: list) -> None:
    linhas = [
        '"""GERADO AUTOMATICAMENTE por gerar_imagens.py -- nao edite na mao.',
        "Rode `python gerar_imagens.py` de novo apos capturar/renomear um print.",
        '"""',
    ]
    constantes_usadas = {}  # constante -> arquivo que a gerou primeiro (deteccao de colisao entre fases)
    for nome_arquivo in arquivos:
        stem = os.path.splitext(os.path.basename(nome_arquivo))[0]
        constante = "IMG_" + stem.upper().replace(" ", "_")
        if not constante.isidentifier():
            logger.warning(
                "\n%s\nPRINT IGNORADO: '%s' geraria a constante invalida '%s'.\n"
                "Renomeie o arquivo (letras, numeros e _ apenas) e execute de novo.\n%s",
                "=" * 30, nome_arquivo, constante, "=" * 30,
            )
            continue
        if constante in constantes_usadas:
            logger.warning(
                "\n%s\nPRINT IGNORADO: '%s' geraria a constante '%s', ja usada por '%s'.\n"
                "Renomeie um dos dois arquivos e execute de novo.\n%s",
                "=" * 30, nome_arquivo, constante, constantes_usadas[constante], "=" * 30,
            )
            continue
        constantes_usadas[constante] = nome_arquivo
        linhas.append(f'{constante} = "{nome_arquivo}"')

    os.makedirs(os.path.dirname(CAMINHO_GERADO), exist_ok=True)
    with open(CAMINHO_GERADO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def gerar() -> list:
    atuais = _listar_imagens()
    if atuais != _arquivos_no_gerado():
        _escrever(atuais)
    return atuais


if __name__ == "__main__":
    arquivos = gerar()
    print(f"{len(arquivos)} imagem(ns) -> {CAMINHO_GERADO}")
