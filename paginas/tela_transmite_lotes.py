"""Fase 2 -- transmissão dos lotes - tela "Nota Fiscal de Serviço Eletrônica (NFS-e)"
"""
import logging
import time

from excecoes import ErroNaTela
from paginas import imagens_geradas as img
from paginas.tela import Tela

logger = logging.getLogger(__name__)


class TelaTransmiteLotes(Tela):

    def abrir_tela_envio_nfs(self) -> bool:
        """Navega do menu principal até a tela NFS-e. Devolve se a tela
        abriu de fato"""
        self._combo("alt", "right", "up", "up", "enter")
        return self._visivel(img.IMG_TELA_PRINCIPAL_NFS, timeout=2)

    def selecionar_posicao(self, posicao: int) -> None:
        """Seleciona a linha da grid na posição (0-based) indicada.
        'Home' garante partir sempre da primeira linha, independente de
        onde o cursor estava antes -- depois 'ArrowDown' x posição chega
        exatamente na linha alvo, sem precisar contabilizar linhas
        puladas nem rastrear onde a seleção ficou da última vez.
        """
        self._combo("home")
        self._combo("down", repetir=posicao, intervalo=0)

    def _localizar_lote(self, lote_codigo) -> None:
        """Digita o código no campo Lote (já vem focado ao abrir a tela),
        confirma e sai até a grid de notas. Só roda uma vez por lote --
        depois de 'Gravar', o foco volta direto pro campo Lote (sem
        precisar digitar de novo), então voltar pra grid é só 1
        Shift+Tab (ver alterar_datas_emissao_necessarias)."""
        self._digitar(lote_codigo)
        self._combo("enter")
        self._combo(("shift", "tab"), repetir=2)  # do campo Lote (pos-Enter) até a grid

    def alterar_datas_emissao_necessarias(self, lote_codigo, posicoes, data_ddmmaaaa: str) -> None:
        """Corrige a data de emissão de cada posição indicada, digitando
        'data_ddmmaaaa'. 'posicoes' é uma lista de índices 0-based, na
        mesma ordem da grid (ver ConsultaDados.obter_notas_do_lote) --
        quem decide QUAIS posições corrigir e QUAL data usar é o
        Processo, aqui só executa.

        Depois de 'Gravar', o foco volta sozinho pro campo Lote com o
        texto selecionado -- deixado assim de propósito após a ÚLTIMA
        posição, já pronto pra 'localizar_lote' do PRÓXIMO lote sem
        precisar digitar por cima de nada. Só volta pra grid (1
        Shift+Tab) antes de selecionar a próxima posição, quando ainda
        sobra alguma nesse mesmo lote.
        """

        for indice, posicao in enumerate(posicoes):
            if indice > 0:
                self._combo(("shift", "tab"))  # do campo Lote (selecionado, pos-Gravar) de volta pra grid
            self.selecionar_posicao(posicao)
            self._clicar_imagem(img.IMG_ALTERAR, self.timeouts["clicar_alterar"])
            self._combo("tab", repetir=2)          # até o campo Data
            self._digitar(data_ddmmaaaa)
            self._clicar_imagem(img.IMG_GRAVAR, self.timeouts["clicar_alterar"])
            self._sumir(img.IMG_GRAVAR, self.timeouts["clicar_alterar"])  # confirma que a tela da NF fechou

    def transmitir(self) -> None:
        """Dispara a transmissao do lote e espera ela terminar. Terminou =
        rodape da tela de notas visivel CONTINUAMENTE por
        'rodape_estavel_transmissao' segundos -- durante o processamento as
        telas piscam e o rodape aparece e some, entao so a presenca continua
        conta. Nao olha o banco: o que recebeu NFS-e ou nao, o Processo
        confere depois.
        """
        logger.info('começou transmitir')
        self._clicar_imagem(img.IMG_TRANSMITIR, timeout=3)
        self._clicar_imagem(img.IMG_TRANSMITIR, timeout=3)
        self._clicar_imagem(img.IMG_DESEJA_TRANSMITIR_LOTES_AGORA, timeout=3)
        self._atalho('enter')

        # Nova versão do Simbolus eliminou essas telas
        # self._clicar_imagem(img.IMG_VISUALIZAR_RPS_ANTES, timeout=3)
        # self._combo('tab', 'enter')
        # self._clicar_imagem(img.IMG_DESEJA_TRANSMITIR_AGORA, timeout=3)
        # self._atalho('enter')

        self._dispensar_telas_caoticas()

        # Confirma que a transmissao comecou de fato -- so a partir daqui o
        # rodape estavel significa "terminou", e nao "ainda nem saiu da grid".
        self._esperar((img.IMG_AGUARDE_TRANSMITINDO, img.IMG_ALGUM_ERRO), 5)

        teto = self.timeouts["teto_transmissao_lote"]
        estavel = self.timeouts["rodape_estavel_transmissao"]
        inicio = time.monotonic()
        while time.monotonic() - inicio < teto:
            if self._achar(img.IMG_DANF_SE) is not None:
                time.sleep(.3)
                self._combo('alt', 'f')
            self._dispensar_telas_caoticas()
            if self._visivel_estavel(img.IMG_RODAPE_TELA_NOTAS, estavel):
                logger.info("transmissao concluida em %.0fs", time.monotonic() - inicio)
                return
            time.sleep(self.pausa)
        raise ErroNaTela(f"transmissao nao concluiu em {teto:.0f}s", print=True)
        # return self._esperar((img.IMG_LOTE_EXCLAMA, img.IMG_LOTE_TRANSMITIDO_SUCESSO), self.timeouts["aguardar_transmissao"])

    def _transmitido_com_sucesso(self, lote_codigo) -> bool:
        """Confirma o aviso de sucesso e aguarda o relatório salvar.
        Devolve False -- nunca é erro confirmado."""
        logger.info(f'_transmitido_com_sucesso: {lote_codigo}')
        self._atalho('enter') # "OK" no aviso de "Lote transmitido com sucesso"
        self._esperar(img.IMG_CONFIRMACAO_DESEJA_CONSULTAR_RPS_PROTOCOLAR_NOTAS, 3)
        self._combo('tab', 'enter')

        self._esperar_com_intermitencia(None, img.IMG_SALVANDO_RELATORIO_AGUARDE, 30, 3.5)
        return False

    def _transmitido_com_erro(self, lote_codigo) -> bool:
        """"Lote !" pode ser falso positivo -- consulta uma nota
        especifica pra confirmar antes de tratar como erro de verdade.
        Devolve True só quando o erro for confirmado (nem a nota
        especifica foi transmitida) -- ai o lote ja sai daqui com o
        protocolo de tentativa limpo, pronto pra reprocessar depois.
        """
        logger.info(f'_transmitido_com_erro: {lote_codigo}')
        self._clicar_imagem(img.IMG_NAO_TRANSMITIDO)
        self._atalho('enter') # "OK" no aviso de "Lote !"

        self._clicar_imagem(img.IMG_CONSULTAR, 3)
        self._clicar_imagem(img.IMG_CONSULTAR, 3) # bug tela desfocada - dois cliques no botão

        self._esperar_com_intermitencia((img.IMG_NAO_TRANSMITIDO, img.IMG_NFSE_TRANSMITIDA), img.IMG_SALVANDO_RELATORIO_AGUARDE, 15, 2.5)
        time.sleep(1)
        logger.debug('esperou proc consulta única')
        if self._esperar(img.IMG_NFSE_TRANSMITIDA, 2):
            logger.debug('deu bom pós proc consulta única')
            self._atalho('enter')
            self._achar(img.IMG_DESEJA_IMPRIMIR_ESTA_NFSE, 3) # já vem focado no "Não"
            self._atalho('enter')

            self._clicar_imagem(img.IMG_CONSULTAR_TODOS, 3)
            self._clicar_imagem(img.IMG_CONSULTAR_TODOS, 3) # bug tela desfocada - dois cliques no botão
            self._esperar_com_intermitencia((img.IMG_NAO_TRANSMITIDO, img.IMG_NFSE_TRANSMITIDA), img.IMG_SALVANDO_RELATORIO_AGUARDE, 20, 2.5)

            return False  # falso positivo -- ja transmitido de verdade
        
        elif self._achar(img.IMG_NAO_TRANSMITIDO, 2):
            logger.debug('deu ruim pós proc consulta única')
            self._atalho('enter') # Na caixa de "Não transmitida" e volta ao fluxo
            self._limpar_lote()

            return True

    def _limpar_lote(self) -> None:
        """Limpa o protocolo da tentativa de transmissao malsucedida,
        deixando o lote pronto pra ser reprocessado depois."""
        logger.debug('limpa lote')
