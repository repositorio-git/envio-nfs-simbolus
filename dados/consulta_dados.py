"""A MEMORIA: todo acesso a dado externo (banco, API, arquivo) mora aqui.
Processo consulta; nunca monta SQL/chamada externa ele mesmo.

Backend deste projeto: Firebird do Simbolus via fdb (INT-02). A regra que
nao muda com o driver: sempre bind variables, nunca concatenacao de string
-- no fdb o marcador e '?' posicional, nao ':nome'.
"""
import logging
import os
from datetime import datetime, timedelta

import fdb

logger = logging.getLogger(__name__)


class ConsultaDados:
    def __init__(self, config: dict):
        self.config = config
        # Conexao vem toda do .env, nao da config: INT-02 e RNF-08 exigem
        # host, porta, database, usuario e senha fora do codigo versionado.
        self.host = os.environ.get("FIREBIRD_HOST")
        self.porta = int(os.environ.get("FIREBIRD_PORT", 3050))
        self.database = os.environ.get("FIREBIRD_DATABASE")
        self.usuario = os.environ.get("FIREBIRD_USUARIO", "SYSDBA")
        self.senha = os.environ.get("FIREBIRD_SENHA")
        if not self.senha:
            logger.warning("FIREBIRD_SENHA nao definida no ambiente/.env")

    def _conectar(self):
        return fdb.connect(
            host=self.host, port=self.porta, database=self.database,
            user=self.usuario, password=self.senha, charset="UTF8",
        )

    def obter_lotes_pendentes(self, dias_retroativos: int = 1) -> list:
        """Lotes ja gerados (NFSE_LOTE) ainda sem protocolo de transmissao
        confirmado e sem nenhuma nota com NFS-e ja atribuida -- base do
        loop principal da Fase 2. 'dias_retroativos' limita a janela de
        'lote_data' pra nao arrastar lotes antigos demais a cada execucao;
        quem decide esse numero e o Processo (ou a config), nao esta
        chumbado aqui.

        Devolve lista de (lote_codigo, lote_data).
        """
        # 'CURRENT_TIMESTAMP - ?' no SQL faz o Firebird inferir o parametro
        # como TIMESTAMP (contexto aritmetico), nao como numero -- o fdb
        # entao tenta converter o int como se fosse data e estoura
        # ValueError. Calculando a data de corte aqui e passando um
        # datetime de verdade evita essa inferencia de tipo ambigua.
        corte = datetime.now() - timedelta(days=dias_retroativos)
        con = self._conectar()
        try:
            cur = con.cursor()

            cur.execute(
                """
                 SELECT rps.lote_codigo, lot.lote_data, COUNT(*) AS qt_notas
              FROM NFSE_RPS rps
              JOIN NFSE_LOTE lot ON lot.lote_codigo = rps.lote_codigo
              where rps.rps_numero_nfse is null
               and lot.lote_data > CURRENT_TIMESTAMP - 4
               AND lot.lote_protocolo IS NULL
               and rps.rps_competencia > CURRENT_TIMESTAMP - 4
               and rps.rps_competencia < CURRENT_TIMESTAMP
             GROUP BY rps.lote_codigo, lot.lote_data
                """
            ) # and lot.lote_codigo not in (56011)
            candidatos = [(linha[0], linha[1]) for linha in cur.fetchall()]
            if not candidatos:
                return []

            # Nenhum indice de NFSE_RPS cobre lote_codigo + rps_numero_nfse
            # juntos, e o otimizador do Firebird (estatistica desatualizada
            # nesse banco) nao usa indice nenhum aqui de qualquer forma --
            # confirmado: um filtro de so 3 lote_codigo via JOIN/NOT EXISTS
            # levou 8s (uma varredura completa POR lote candidato), contra
            # 2s de uma varredura unica sem JOIN. Por isso aqui e uma
            # varredura so, sem correlacionar com 'candidatos' dentro do
            # SQL -- o cruzamento (so importa pra quem tambem esta em
            # 'candidatos', que ja veio filtrado por data) e feito em
            # Python logo abaixo.
            cur.execute("""
                SELECT DISTINCT lote_codigo FROM NFSE_RPS
                 WHERE rps_numero_nfse IS NOT NULL 
                   and rps_competencia > CURRENT_TIMESTAMP - 5
                   and rps_competencia < CURRENT_TIMESTAMP + 1 """)
            ja_com_nfse = {linha[0] for linha in cur.fetchall()}

            lotes = [(codigo, data) for codigo, data in candidatos if codigo not in ja_com_nfse]
            return sorted(lotes)
        finally:
            con.close()

    def obter_lotes_gerados_hoje(self) -> list:
        """Lotes gerados nas ultimas 24h -- base do e-mail de backup da
        Fase 1 (RF-18). 'lote_data > CURRENT_TIMESTAMP - 1' confirmado
        pelo usuario contra o banco real. Ao contrario de
        'obter_lotes_pendentes', aqui interessa TODO lote gerado nesse
        intervalo, transmitido ou nao -- sem filtro de protocolo.

        Devolve lista de (lote_codigo, qt_notas).
        """
        sql = """
            SELECT rps.lote_codigo, COUNT(*) AS qt_notas
              FROM NFSE_RPS rps
              JOIN NFSE_LOTE lot ON lot.lote_codigo = rps.lote_codigo
             WHERE lot.lote_data > CURRENT_TIMESTAMP - 1
             GROUP BY rps.lote_codigo
             ORDER BY rps.lote_codigo
        """
        con = self._conectar()
        try:
            cur = con.cursor()
            cur.execute(sql)
            return cur.fetchall()
        finally:
            con.close()

    def obter_lotes_parciais(self, dias_retroativos: int = 4) -> list:
        """Lotes com envio parcial: pelo menos uma RPS ja com numero de
        NFS-e e pelo menos uma ainda sem. Nao usa lote_protocolo -- o
        Simbolus deixa esse campo nulo mesmo em lote transmitido inteiro.
        'obter_lotes_pendentes' descarta lote com qualquer NFS-e, entao um
        parcial nunca e retransmitido: este e o unico lugar onde ele aparece.

        Devolve lista de (lote_codigo, qt_notas_sem_nfse).
        """
        corte = datetime.now() - timedelta(days=dias_retroativos)
        # COUNT(coluna) ignora nulos: COUNT(*) - COUNT(rps_numero_nfse) e
        # quantas RPS do lote ainda estao sem NFS-e.
        sql = """
            SELECT rps.lote_codigo, COUNT(*) - COUNT(rps.rps_numero_nfse) AS qt_sem_nfse
              FROM NFSE_RPS rps
              JOIN NFSE_LOTE lot ON lot.lote_codigo = rps.lote_codigo
             WHERE lot.lote_data > ?
             GROUP BY rps.lote_codigo
            HAVING COUNT(rps.rps_numero_nfse) > 0
               AND COUNT(rps.rps_numero_nfse) < COUNT(*)
             ORDER BY rps.lote_codigo
        """
        con = self._conectar()
        try:
            cur = con.cursor()
            cur.execute(sql, (corte,))
            return cur.fetchall()
        finally:
            con.close()

    def obter_lotes_transmitidos_com_sucesso(self, dias_retroativos: int = 4) -> list:
        """Contrario de 'obter_lotes_parciais': lotes com TODAS as RPS ja
        com numero de NFS-e atribuido. Base do e-mail de sucesso ao final
        da Fase 2. Sem lote_protocolo, pelo mesmo motivo dos parciais.

        Devolve lista de (lote_codigo, qt_notas).
        """
        corte = datetime.now() - timedelta(days=dias_retroativos)
        sql = """
            SELECT rps.lote_codigo, COUNT(*) AS qt_notas
              FROM NFSE_RPS rps
              JOIN NFSE_LOTE lot ON lot.lote_codigo = rps.lote_codigo
             WHERE lot.lote_data > ?
             GROUP BY rps.lote_codigo
            HAVING COUNT(rps.rps_numero_nfse) = COUNT(*)
             ORDER BY rps.lote_codigo
        """
        con = self._conectar()
        try:
            cur = con.cursor()
            cur.execute(sql, (corte,))
            return cur.fetchall()
        finally:
            con.close()

    def obter_notas_do_lote(self, lote_codigo) -> list:
        """Todas as notas (rps_numero, rps_competencia) de um lote, na
        mesma ordem em que aparecem na grid da tela NFS-e (rps_numero
        ascendente, confirmado contra a tela real). O indice de uma nota
        nessa lista e a mesma posicao dela na grid -- base pra navegar
        ate ela via teclado (Home + ArrowDown x indice).
        """
        sql = (
            "SELECT rps_numero, rps_competencia FROM NFSE_RPS "
            "WHERE lote_codigo = ? ORDER BY rps_numero"
        )
        con = self._conectar()
        try:
            cur = con.cursor()
            cur.execute(sql, (lote_codigo,))
            return cur.fetchall()
        finally:
            con.close()

    def contar_notas_sem_nfse(self, lote_codigo) -> int:
        """Quantidade de notas do lote ainda sem numero de NFS-e
        atribuido pela prefeitura (rps_numero_nfse nulo) -- usado pra
        acompanhar o processamento assincrono apos a transmissao, ate
        todas as notas do lote receberem seu numero de NFS-e.
        """
        sql = (
            """
            SELECT COUNT(*) AS qt_notas
              FROM NFSE_RPS rps
              JOIN NFSE_LOTE lot ON lot.lote_codigo = rps.lote_codigo
             WHERE lot.lote_codigo = ?
               AND rps.rps_numero_nfse IS NULL
            """
        )
        con = self._conectar()
        try:
            cur = con.cursor()
            cur.execute(sql, (lote_codigo,))
            return cur.fetchone()[0]
        finally:
            con.close()
