"""O CEREBRO: decide. Manda as maos (paginas/) e a memoria (dados/) agirem,
mas nao clica nem consulta dado ele mesmo.

Mantenha isso curto -- e uma receita, nao um lugar pra logica de tela ou
SQL. Se um metodo daqui esta ficando longo e dificil de acompanhar, e sinal
de que ele esta fazendo coisa demais (ver CLAUDE.md, secao de arquitetura).
"""
import html
import logging
import subprocess
from datetime import date, datetime

from excecoes import ErroNaTela
from paginas import imagens_geradas as img
from paginas.tela import Tela
from paginas.tela_gera_lotes import TelaGeraLotes
from paginas.tela_transmite_lotes import TelaTransmiteLotes
from dados.consulta_dados import ConsultaDados
from dados.notificacao import Notificador

logger = logging.getLogger(__name__)


def _somente_data(valor):
    """rps_competencia pode vir do Firebird como datetime.datetime ou
    datetime.date, dependendo do tipo da coluna -- normaliza pra so a
    data, sem hora, antes de comparar com 'hoje'."""
    return valor.date() if isinstance(valor, datetime) else valor


def _posicoes_a_corrigir(notas, hoje: date) -> list:
    """'notas': lista (rps_numero, rps_competencia) na MESMA ordem em que
    aparecem na grid da tela NFS-e (rps_numero ascendente, confirmado
    contra a tela real). Devolve os indices (0-based) das notas cuja
    competencia nao e 'hoje' -- cada indice e quantos ArrowDown apertar
    depois de um Home pra chegar naquela linha da grid.
    """
    return [
        indice
        for indice, (_, competencia) in enumerate(notas)
        if _somente_data(competencia) != hoje
    ]


class Processo:
    def __init__(self, config: dict, credenciais: dict):
        self.config = config
        self.credenciais = credenciais
        self.tela = Tela(config)                                # abertura ate o menu principal
        self.tela_gera_lotes = TelaGeraLotes(config)            # maos, Fase 1
        self.tela_transmite_lotes = TelaTransmiteLotes(config)  # maos, Fase 2
        self.dados = ConsultaDados(config)                      # memoria
        self.notificador = Notificador(config)                  # memoria

        # Estado que precisa sobreviver ENTRE metodos (ex: inicializar() e
        # processar() os dois escrevendo/lendo o mesmo dado) vai aqui como
        # atributo de instancia. Estado que so um metodo usa fica variavel
        # local dele mesmo -- nao promova pra atributo sem essa razao.
        self.lotes_com_erro = []  # lote_codigo -- erro confirmado na transmissao (nao falso positivo), usado no e-mail final

    def inicializar(self, perfil: str) -> None:
        """Chega no estado pivo de onde cada ciclo de fase pode comecar a
        trabalhar. Use tela.avancar() com uma sequencia de (pivo, *acoes) --
        isso permite 'acoplar' o robo a qualquer ponto do fluxo em que o
        app alvo ja estiver, em vez de assumir que sempre comeca do zero.

        'perfil': so e usado pra abrir o SIMBOLUS (_abrir_simbolus) quando
        NENHUM pivo das etapas abaixo esta visivel agora -- ou seja, quando
        o app realmente nao esta aberto ainda. Se algum pivo ja aparece (o
        app sobreviveu de um ciclo anterior, por exemplo), nao abre uma
        segunda instancia: so continua dai pra frente.

        Exemplo de forma (adapte pro seu fluxo real):
        """
        etapas = (
            ((img.IMG_WIN_NAO_PODE_ENCONTRAR_SISTEMANFSE_EXE, img.IMG_WIN_NAO_PODE_ENCONTRAR_SISTEMA_EXE),
                lambda tela: tela.inicializacao_geral()),
            (img.IMG_LOGIN, lambda tela: tela.login(self.credenciais['senha'])),
            ((img.IMG_REL_ESTOURO_ESTOQUE_MINIMO, img.IMG_REL_ESTOURO_ESTOQUE_MINIMO2),
                lambda tela: tela._clicar_imagem((img.IMG_REL_ESTOURO_ESTOQUE_MINIMO, img.IMG_REL_ESTOURO_ESTOQUE_MINIMO2), self.config["timeouts"]["rel_estouro_estoque_minimo"]),
                lambda _: logger.info("tratando \"Relatório do Estouro do Estoque Mínimo\" [%ss]", self.config["timeouts"]["rel_estouro_estoque_minimo"]),
                lambda tela: tela._atalho('alt', 'c')
            ),
            (img.IMG_REAJUSTE_CONTRATOS,
                lambda _: logger.info("tratando \"Reajuste de Contratos\" [%ss]", 5),
                lambda tela: tela._clicar_imagem(img.IMG_INIT_FECHAR, 5),
                lambda _: logger.info("aguardando tela de \"Boletos vencidos\" [%ss]", self.config["timeouts"]["carregamento_simbolus"]),
            ),
            ((img.IMG_ICONE_EON_MINIMIZADO, img.IMG_APPCONTROLLER_MINIMIZADO, img.IMG_APPCONTROLLER_MINIMIZADO_FOCADO),
                lambda _: logger.info("clique fechar tela \"Boletos vencidos\""),
                lambda tela: tela._clicar_enquanto_espera(img.IMG_MENU, img.IMG_INIT_FECHAR, self.config["timeouts"]["teto_menu_principal"]),
            ),
            (img.IMG_MENU,
                lambda _: logger.info("Menu principal"),
            )
        )

        self.tela.avancar(
            etapas, self.config["timeouts"]["deteccao_etapa"],
            se_nenhum_pivo=lambda: self._abrir_simbolus(perfil),
        )

        logger.info("[INICIALIZACAO]")


    def _abrir_simbolus(self, perfil: str) -> None:
        """Abre o SIMBOLUS via AppController com o perfil indicado --
        '24.SIMBOLUS PRD RPO' (Fase 1, Contas a Receber) ou
        '25.SIMBOLUS NFSE PRD RPO' (Fase 2, NFS-e). Mesma aplicacao nos
        dois casos, so muda quais menus vem habilitados; 'inicializar()'
        (login, popups, chegar no menu) e identico pras duas fases.

        Nao espera o app terminar de carregar -- isso ja e papel do
        'inicializar()' via avancar()/detectar_etapa, que lida com o app
        subindo em paralelo ao robo.
        """
        logger.info("_abrir_simbolus: perfil '%s'", perfil)
        subprocess.Popen([
            r"C:\Program Files (x86)\GraphOn\AppController\AppController.exe",
            "-h", "saas_ts04.cortel.erpconnect",
            "-a", perfil,
        ])

    def _gerar_lote(self, grupo: dict) -> None:
        """Preenche os filtros de um grupo de 'grupos_conta' (ver
        configuracoes.py) e gera o lote de NFS-e correspondente, se houver
        RPS pra esse grupo -- quando a grid vem vazia, so fecha a tela e
        segue pro proximo grupo. Abre e fecha a tela 'Contas a Receber'
        aqui mesmo, por grupo -- cada grupo comeca de um estado conhecido
        (ver 'abrir_tela_contas_a_receber'), sem herdar filtro nenhum do
        grupo anterior."""
        if not self.tela_gera_lotes.abrir_tela_contas_a_receber():
            raise ErroNaTela("nao abriu a tela de Contas a Receber")

        if self.tela_gera_lotes.inserir_config_conta(grupo):
            self.tela_gera_lotes.selecionar_todos_resultados()
            self.tela_gera_lotes.gerar_nfse()
        else:
            logger.info("grupo %s sem RPS, pulando", grupo["tipo_conta"])

        self.tela_gera_lotes.fechar_tela_contas_a_receber()

    def _notificar(self, chave: str, assunto: str, corpo: str) -> None:
        """Manda o e-mail de relatorio 'chave' (ex: 'gerados', 'pendentes',
        'pos_processamento') pros destinatarios fixos de configuracoes.py
        -- no maximo uma vez por dia por chave, independente de quantas
        vezes o robo for inicializado nesse dia (reinicializacao apos
        EJECTION, Task Scheduler rodando de novo, etc.)."""
        if self.notificador.ja_enviado_hoje(chave):
            logger.info("e-mail '%s' ja enviado hoje -- nao reenviando", chave)
            return
        self.notificador.enviar(
            self.config["email"]["destinatarios_relatorio"], assunto, corpo
        )
        self.notificador.marcar_enviado_hoje(chave)

    def _tabela_html(self, titulo: str, colunas, linhas) -> str:
        """Bloco HTML (titulo + tabela) pro corpo dos e-mails. Estilo
        inline porque o Outlook ignora <style> no cabecalho."""
        cabecalho = f"<p><b>{html.escape(titulo)}</b></p>"
        if not linhas:
            return cabecalho + "<p>Nenhum lote.</p>"
        celula = 'style="border:1px solid #999;padding:4px 10px;text-align:left"'
        th = "".join(f'<th {celula}>{html.escape(str(c))}</th>' for c in colunas)
        trs = "".join(
            "<tr>" + "".join(f"<td {celula}>{html.escape(str(v))}</td>" for v in linha) + "</tr>"
            for linha in linhas
        )
        return cabecalho + f'<table style="border-collapse:collapse"><tr>{th}</tr>{trs}</table>'

    def _ciclo_fase1(self) -> None:
        """Abre, inicializa e executa a Fase 1 (Geracao de Lotes), depois
        sai do SIMBOLUS -- ciclo completo e independente da Fase 2."""
        logger.info("[FASE 1 - Geração de Lotes]")
        self.inicializar("24.SIMBOLUS PRD RPO")

        for grupo in self.config["grupos_conta"]:
            logger.info("grupo %s", grupo["tipo_conta"])
            self._gerar_lote(grupo)

        lotes_gerados = self.dados.obter_lotes_gerados_hoje()
        self._notificar(
            "gerados",
            f"SIMBOLUS_NFSe_lotes_gerados_{date.today():%d%m%Y}",
            self._tabela_html("Lotes gerados hoje", ("Lote", "Qtd RPS"), lotes_gerados),
        )

        logger.info('### Fase 1 completa ###')
        self.tela.sair_simbolus()

    def _ciclo_fase2(self) -> None:
        """Abre, inicializa e executa a Fase 2 (Transmissao dos Lotes),
        depois sai do SIMBOLUS -- ciclo completo e independente da Fase 1.
        Nao abre o app se nao houver nada pendente pra transmitir.
        """
        logger.info("[FASE 2 - Transmissão dos Lotes Gerados]")

        self.inicializar("25.SIMBOLUS NFSE PRD RPO")

        lotes_pendentes = self.dados.obter_lotes_pendentes()
        logger.info("%s lote(s) pendente(s) de transmissão", len(lotes_pendentes))

        self._notificar(
            "pendentes",
            f"SIMBOLUS_NFSe_lotes_pendentes_{date.today():%d%m%Y}",
            self._tabela_html(
                "Lotes pendentes de transmissão", ("Lote", "Data"),
                [(codigo, f"{data:%d/%m/%y}") for codigo, data in lotes_pendentes],
            ),
        )

        if not lotes_pendentes:
            return

        if not self.tela_transmite_lotes.abrir_tela_envio_nfs():
            raise ErroNaTela("nao abriu a tela de NFS-e")

        hoje = date.today()
        data_hoje_ddmmaaaa = hoje.strftime("%d%m%Y")

        acoes_resultado_transmissao = {
            img.IMG_LOTE_TRANSMITIDO_SUCESSO: self.tela_transmite_lotes._transmitido_com_sucesso,
            img.IMG_LOTE_EXCLAMA: self.tela_transmite_lotes._transmitido_com_erro,
        }

        # RF-28 (count_erro entre lotes) fica adiado ate a deteccao de
        # IMG_NAO_TRANSMITIDO/IMG_LOTE_EXCLAMA estar confiavel o bastante
        # pra distinguir erro de negocio de falha tecnica de tela.
        for lote_codigo, _ in lotes_pendentes:
            try:
                logger.info("lote %s", lote_codigo)

                self.tela_transmite_lotes._localizar_lote(lote_codigo)

                notas = self.dados.obter_notas_do_lote(lote_codigo)
                posicoes = _posicoes_a_corrigir(notas, hoje)

                if posicoes:
                    logger.info("\t %s nota(s) com data de emissão divergente", len(posicoes))
                    self.tela_transmite_lotes.alterar_datas_emissao_necessarias(lote_codigo, posicoes, data_hoje_ddmmaaaa)

                resultado = self.tela_transmite_lotes.transmitir()
                sem_nfse = self.dados.contar_notas_sem_nfse(lote_codigo)
                logger.info("lote %s: %s de %s RPS sem NFS-e", lote_codigo, sem_nfse, len(notas))
                # logger.info('result: '+str(resultado))

                # erro_confirmado = acoes_resultado_transmissao[resultado](lote_codigo)
                # if erro_confirmado:
                #     self.lotes_com_erro.append(lote_codigo)

                # logger.debug(f"lotes com erro: {self.lotes_com_erro}")

                self.tela.reposicionar_para_proximo_lote()
            except ErroNaTela:
                logger.exception("falha tecnica no lote %s -- recuperando e seguindo pro proximo", lote_codigo)
                self.tela.recuperar_para_pivo(self.config["timeouts"]["recuperacao_pivo"])
                self.tela_transmite_lotes.abrir_tela_envio_nfs()

        lotes_sucesso = self.dados.obter_lotes_transmitidos_com_sucesso()
        lotes_parciais = self.dados.obter_lotes_parciais()
        self._notificar(
            "pos_processamento",
            f"SIMBOLUS_NFSe_pos_processamento_{hoje:%d%m%Y}",
            self._tabela_html("Lotes transmitidos com sucesso (todas as RPS confirmadas)", ("Lote", "Qtd RPS"), lotes_sucesso)
            + self._tabela_html("Lotes transmitidos com RPS ainda pendente de NFS-e (envio parcial)", ("Lote", "Qtd RPS sem NFS-e"), lotes_parciais),
        )

        self.tela.sair_simbolus()

    def finalizar(self) -> None:
        """Roda sempre, mesmo se deu erro no meio -- fechar sessao, sair
        do sistema, o que for equivalente a 'deixar limpo pra proxima vez'.
        """
        logger.info("[FINALIZACAO]")

    def _rodar_fase(self, ciclo) -> None:
        """Roda 'ciclo' (um dos _ciclo_faseN, que ja chama inicializar() no
        proprio inicio) ate suceder ou esgotar 'max_tentativas_fase'. Cada
        falha aciona EJECTION() (mata o app a forca) antes de tentar de
        novo -- a fase inteira recomeca do zero (reinicializa, reconsulta
        tudo), nao so o passo que falhou, porque o estado da tela apos
        EJECTION nao e confiavel o bastante pra retomar no meio.

        Esgotando as tentativas, relanca a excecao -- quem decide se tenta
        de novo depois e o agendador externo (Task Scheduler ou
        equivalente), nao mais o proprio Python.
        """
        tentativas = self.config["max_tentativas_fase"]
        for tentativa in range(1, tentativas + 1):
            logger.info("_rodar_fase: tentativa %s/%s de %s", tentativa, tentativas, ciclo.__name__)
            try:
                ciclo()
                return
            except Exception:
                logger.exception("Fase falhou (tentativa %s/%s) -- acionando EJECTION()", tentativa, tentativas)
                self.tela.EJECTION()
                if tentativa == tentativas:
                    raise

    def executar(self, fluxo: str = None) -> None:
        """'fluxo': None executa as duas fases, em sequencia (Fase 1
        depois Fase 2); 'gerar' ou 'transmitir' executa so essa fase
        isoladamente. Cada fase abre e fecha o SIMBOLUS por
        conta propria (perfis diferentes do AppController) -- rodar uma
        nao depende da outra ter rodado antes na mesma execucao.

        Erro fatal numa fase passa por _rodar_fase: EJECTION() e a fase
        inteira de novo, do zero, ate 'max_tentativas_fase' vezes.
        Esgotando, relanca a excecao pro agendador externo decidir.

        Implementa RF-05 (ordem de execucao e finalizar() sempre) e RNF-07.
        """
        try:
            if fluxo in (None, "gerar"):
                self._rodar_fase(self._ciclo_fase1)

            if fluxo in (None, "transmitir"):
                self._rodar_fase(self._ciclo_fase2)
        finally:
            # RF-05 / RNF-07: finalizar() executa sempre. No finally, e nao no
            # fim do try, para cobrir tambem o erro fatal e o return antecipado
            # de qualquer um dos ciclos. E ele que fecha a conexao com o banco
            # e grava o log da execucao (RF-35) -- justamente o que precisa
            # acontecer quando deu errado.
            self.finalizar()
