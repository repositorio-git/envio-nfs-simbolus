"""So um tipo de erro -- versao enxuta.

O REFramework classico usa DUAS classes (ExcecaoNegocio / ExcecaoSistema)
porque processa uma FILA: precisa distinguir "pula esse item e segue" de
"tenta de novo". Se o processo for uma passada linear, sem fila, uma classe
so basta: deu ruim na tela, para e avisa.

Se um dia virar fila, divida em duas. Nao antes.
"""
import logging
import os
import time
from datetime import datetime

import pyautogui
from PIL import ImageGrab

logger = logging.getLogger(__name__)

DIR_ERROS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "erros")


def _capturar_tela() -> str:
    
    os.makedirs(DIR_ERROS, exist_ok=True)
    caminho = os.path.join(DIR_ERROS, f"erro_{datetime.now():%Y%m%d_%H%M%S}.png")

    pyautogui.hotkey("printscreen")
    imagem = ImageGrab.grabclipboard()
    if imagem is None:
        imagem = pyautogui.screenshot()

    imagem.save(caminho)
    return caminho


class ErroNaTela(Exception):
    """Algo esperado nao aconteceu na tela (imagem nao apareceu, etc.).

    Com 'print=True', tenta salvar um print do momento da falha em
    logs/erros/ -- so pra falhas anormais de verdade; muitas destas sao
    esperadas e tratadas pelo chamador, e um print a cada uma delas so
    gera ruido. Se a captura falhar, so loga e segue: a excecao original
    nunca deve ficar escondida por um problema no print.
    """

    def __init__(self, mensagem: str, print: bool = False):
        super().__init__(mensagem)
        if print:
            try:
                caminho = _capturar_tela()
                logger.error("%s -- print salvo em %s", mensagem, caminho)
            except Exception:
                logger.exception("Falha ao capturar print do erro (%s)", mensagem)
