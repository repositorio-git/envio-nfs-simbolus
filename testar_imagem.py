"""Diagnostico: essa imagem e encontrada na tela, e em que confianca?

Rode ANTES de confiar num print. Se so acha abaixo de 0.85, o recorte esta
ruim (pegou borda, foco, texto que muda) -- refaca o recorte.

    python testar_imagem.py gerar/nome_do_print
    python testar_imagem.py transmitir/nome_do_print

(nao ponha .png; ele procura em paginas/imagens/<fase>/nome_do_print.png)

Para capturar os prints, use o proprio Windows: Win+Shift+S, recorte so um
pedaco PEQUENO e fixo do elemento, salve em paginas/imagens/<fase>/ (fase =
"gerar" ou "transmitir") com o nome que a constante IMG_ vai ter (ex:
login.png -> IMG_LOGIN).
"""
import sys
import time
from pathlib import Path

import pyautogui

from configuracoes import CONFIG

if len(sys.argv) < 2:
    sys.exit("uso: python testar_imagem.py <fase>/<nome_sem_extensao>")

caminho = str(Path(CONFIG["caminhos"]["imagens"]) / f"{sys.argv[1]}.png")
if not Path(caminho).exists():
    sys.exit(f"nao existe: {caminho}")

print("Buscando em 2s -- deixe a tela alvo visivel.")
time.sleep(2)

melhor = None
for c in (0.99, 0.95, 0.90, 0.85, 0.80, 0.70):
    try:
        pos = pyautogui.locateCenterOnScreen(caminho, confidence=c)
    except pyautogui.ImageNotFoundException:
        pos = None
    print(f"  confianca {c:.2f} -> {('OK ' + str(tuple(pos))) if pos else 'nao achou'}")
    time.sleep(.3)
    if pos and melhor is None:
        melhor = c

if melhor is None:
    print("\nNao achou. Causas: DPI/resolucao diferente de quando capturou,")
    print("ou o recorte inclui algo que muda. Refaca o recorte menor e fixo.")
else:
    print(f"\nMelhor: {melhor:.2f}. Se for < 0.90, ajuste 'confidence' no configuracoes.py")
