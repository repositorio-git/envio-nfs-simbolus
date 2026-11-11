"""Fase 1 -- geracao dos lotes - tela "Contas a Receber"
"""
import logging
import time
from datetime import datetime

from excecoes import ErroNaTela
from paginas import imagens_geradas as img
from paginas.tela import Tela

logger = logging.getLogger(__name__)


class TelaGeraLotes(Tela):

    def abrir_tela_contas_a_receber(self) -> bool:
        """Navega do menu principal ate a tela 'Contas a Receber' e
        garante o radio 'Filtrar por' = 'Conta' marcado -- esse e o pivo
        fixo de onde toda a sequencia de 'selecionar_conta' em diante
        parte, sempre do mesmo jeito a cada grupo (ver
        'fechar_tela_contas_a_receber': a tela e reaberta do zero pra
        cada grupo, entao esse estado nunca precisa ser inferido do que
        sobrou do grupo anterior). Devolve se a tela abriu de fato."""

        self._combo("alt", "right", "right", "right", "down", "enter")

        if not self._visivel(img.IMG_TELA_CONTAS_A_RECEBER, timeout=2):
            return False
        return True

    def fechar_tela_contas_a_receber(self) -> None:
        """Fecha a tela 'Contas a Receber' -- chamado ao final de CADA
        grupo (nao so no fim da fase inteira), pra cada iteracao comecar
        sempre do estado conhecido garantido por
        'abrir_tela_contas_a_receber', em vez de precisar de condicional
        pra limpar/resetar filtro nenhum."""
        self._combo("esc")

    def inserir_config_conta(self, grupo: dict) -> bool:
        """Preenche os 4 filtros de um grupo de 'grupos_conta' (ver
        configuracoes.py), clica 'Exibir' e espera a grid carregar -- tudo
        em sequencia corrida. O radio 'Filtrar por' ja precisa estar em
        'Conta' ao entrar aqui (garantido por 'abrir_tela_contas_a_receber').
        Os comentarios marcam qual pedaco corresponde a qual filtro da tela.
        Devolve se a grid trouxe algum resultado pra selecionar -- quem
        decide o que fazer com isso (gerar lote ou pular o grupo) e o
        processo, nao esta funcao."""

        # selecionar_conta
        self._clicar_imagem(img.IMG_PAINEL_FILTRAR_POR, 3, -100, -35)
        time.sleep(.5)
        self._clicar_imagem(img.IMG_PAINEL_FILTRAR_POR, 3, -100, -35) # segundo clique por que sim (bugs de foco)

        self._combo("tab") # Posiciona em "Filtrar por Período"

        if grupo["tipo_conta"] == "JAZIGOS":
            self._combo("tab", "up") # Mantém em "Vencimento" e troca "Status" para "Todos"
        else:
            self._combo("tab", "down", "down") # radio em "Pagamento"
    
        self._combo("tab") # posiciona em "Emitidos" - "Todos" já marcado por padrão
        self._combo("tab") # posiciona em "Remessa"  - "Todos" já marcado por padrão
        self._combo("tab", "up")        # posiciona em "Previsão"      , seleciona "Todos"
        self._combo("tab", "up", "tab") # posiciona em "Status Cliente", seleciona "Todos", posiciona em "Conta"

        self._digitar_unicode(grupo["conta"])

        self._combo("tab")  # posiciona em "Período - De:"
        hoje = datetime.now()
        self._digitar(hoje.replace(day=1).strftime("%d%m%Y")) # "De: "
        self._combo("tab")
        self._digitar(hoje.strftime("%d%m%Y")) # "Até: "
        self._combo("tab", "s") # Posiciona em "Notas Fiscais" filtra com S
        self._combo(("alt", "e")) # Botão "Exibir"

        self._esperar(img.IMG_PAINEL_HABILITADO_POS_EXIBIR, self.timeouts["aguardar_carregamento_pos_exibir"])

        return not self._visivel(img.IMG_VAZIO_POS_EXIBIR, timeout=2)

    def selecionar_todos_resultados(self) -> None:
        """Marca o checkbox de 'selecionar tudo' no cabecalho da grid de
        resultados."""
        self._clicar_imagem(img.IMG_MARCAR_TODOS, 3, 0, 20)

    def gerar_nfse(self) -> None:
        """Aciona o botao 'NFS-e' e confirma o popup 'Lote RPS Gerado com
        sucesso'."""

        self._clicar_imagem(img.IMG_NFS_E, 2)

        self._clicar_imagem(img.IMG_LOTE_GERADO_COM_SUCESSO, self.timeouts["aguardar_geracao_lote"])
        self._combo("enter")
