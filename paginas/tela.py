"""As MAOS do robo: so clica, digita e espera a tela. Nao decide nada.

O jeito de esperar e sempre o mesmo: espera pelo que a tela MOSTRA, nunca
por um sleep fixo (que ora e curto demais, ora e longo demais). Os quatro
metodos de baixo (_esperar, _sumir, _visivel, _achar) sao o motor. O resto
sao os passos do SEU processo, montados em cima deles -- ainda nao escritos
aqui (ver "Suas acoes especificas" no final da classe).

Navegacao: sempre que der, use teclado (Tab, Alt+letra, Enter) em vez de
clicar por imagem -- e mais rapido e nao quebra se o DPI mudar. Imagem so
para os pontos de sincronia: saber que uma tela apareceu, que uma acao
confirmou.
"""
import ctypes
import logging
import os
import time

import cv2
import numpy as np
import pyautogui

import subprocess

from excecoes import ErroNaTela
from paginas import imagens_geradas as img

logger = logging.getLogger(__name__)
pyautogui.FAILSAFE = False  # desativado -- maquina de producao roda desatendida, sem ninguem pra mover o mouse de proposito; cursor indo parar no canto por acidente (ex: reconexao de RDP) travava o robo sem motivo real


# Suporte pra '_digitar_unicode': pyautogui.write() so cobre caracteres com
# codigo de tecla virtual no layout de teclado ativo (sem acentuacao, ex:
# 'Ç' vira 'C'). SendInput com KEYEVENTF_UNICODE manda o caractere direto,
# sem passar por esse mapeamento.
class _KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]


class _InputUniao(ctypes.Union):
    # os 3 variants precisam estar presentes mesmo sem usar os outros dois --
    # '_MouseInput' e quem define o tamanho real da union (e o maior dos
    # tres). SendInput usa o tamanho do struct como checagem de seguranca:
    # se nao bater com o sizeof(INPUT) real do Windows, ele rejeita a
    # chamada inteira, sem erro nenhum (falha silenciosa).
    _fields_ = [("ki", _KeyBdInput), ("mi", _MouseInput), ("hi", _HardwareInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("uniao", _InputUniao)]


_INPUT_KEYBOARD = 1
_KEYEVENTF_UNICODE = 0x0004
_KEYEVENTF_KEYUP = 0x0002


class Tela:

    TELAS_CAOTICAS = (
        (img.IMG_ALGUM_ERRO, lambda tela: tela._combo('enter')),
    )

    def __init__(self, config: dict):
        self.conf = config["confidence"]
        self.timeouts = config["timeouts"]
        self.intervalo = config["intervalo_digitacao"]
        self.pausa = config["pausa"]
        self.dir_imagens = config["caminhos"]["imagens"]

    # ===================== motor de espera ===================== #
    def _caminho(self, nome: str) -> str:
        return os.path.join(self.dir_imagens, nome)

    def _achar(self, nome: str, specific_confidence: float = None):
        try:
            # logger.debug('_achar: '+str(nome) )
            conf = self.conf if specific_confidence is None else specific_confidence
            return pyautogui.locateCenterOnScreen(self._caminho(nome), confidence=conf)
        except pyautogui.ImageNotFoundException:
            return None
        except OSError:
            return None

    def _achar_com_transparencia(self, nome: str, specific_confidence: float = None):
        """Como _achar, mas para um template PNG com canal alfa -- pixels
        transparentes nao entram na comparacao. Devolve a caixa inteira
        (left, top, width, height), nao so o centro. Use quando o quadro a
        reconhecer tem uma regiao que muda (um numero, por exemplo) mas o
        resto e fixo.

        pyautogui nao aceita mascara -- chama cv2.matchTemplate direto.
        TM_CCORR_NORMED tem escala de score diferente de TM_CCOEFF_NORMED
        (o que o resto do motor usa): 'specific_confidence' pode precisar
        de um valor calibrado separado, nao o mesmo self.conf de sempre.
        """
        template = cv2.imread(self._caminho(nome), cv2.IMREAD_UNCHANGED)  # BGRA: le tambem o canal alfa
        if template is None or template.shape[2] != 4:
            raise ValueError(f"'{nome}' precisa ser um PNG com canal alfa (RGBA)")

        mascara = template[:, :, 3]        # canal alfa isolado: 0 = ignora, 255 = compara
        template_bgr = template[:, :, :3]  # so B,G,R -- alfa ja extraido acima

        tela = np.array(pyautogui.screenshot())[:, :, ::-1]  # screenshot vem RGB, cv2 espera BGR

        resultado = cv2.matchTemplate(tela, template_bgr, cv2.TM_CCORR_NORMED, mask=mascara)
        _, valor_max, _, pos_max = cv2.minMaxLoc(resultado)

        conf = self.conf if specific_confidence is None else specific_confidence
        if valor_max < conf:
            return None

        altura, largura = template_bgr.shape[:2]
        return pyautogui.Box(pos_max[0], pos_max[1], largura, altura)

    def _dispensar_telas_caoticas(self) -> bool:
        """Avisos de TELAS_CAOTICAS -- podem aparecer em QUALQUER ponto do
        fluxo. Chamado pelo motor a cada volta de espera, entao 'a qualquer
        momento' e coberto sem precisar de um ponto de chamada em cada
        lugar do fluxo onde isso pudesse acontecer.

        Para cada (imagens, *passos): 'imagens' e uma imagem so ou uma
        tupla de imagens alternativas -- encontrar QUALQUER uma delas conta
        como esse aviso. Encontrando, executa cada passo na ordem (cada um
        e um callable que recebe a Tela), cada um protegido por try/except
        pra uma falha num passo nao travar os outros. Nao encontrar
        nenhuma, pula pra proxima -- caso normal, nao e erro.
        """
        for imagens, *passos in self.TELAS_CAOTICAS:
            if isinstance(imagens, str):
                imagens = (imagens,)
            if not any(self._achar(nome, 0.95) is not None for nome in imagens):
                continue
            logger.info("aviso '%s' tratado (%s passo(s))", imagens, len(passos))
            for passo in passos:
                try:
                    passo(self)
                except Exception as e:
                    logger.error(f"Enquanto tratando {imagens}, erro: {e}")

    def _achar_qualquer(self, nomes):
        """nomes: tupla de imagens alternativas. Devolve (nome, posicao) da
        primeira encontrada, ou (None, None) se nenhuma."""
        for nome in nomes:
            pos = self._achar(nome)
            if pos is not None:
                return nome, pos
        return None, None

    def _esperar(self, nome, timeout: float) -> str:
        """Espera a imagem APARECER. 'nome' pode ser uma imagem só ou uma
        tupla de imagens alternativas -- basta UMA aparecer. Devolve QUAL
        imagem apareceu (útil quando 'nome' é uma tupla e quem chamou
        precisa decidir com base em qual delas foi). Estoura ErroNaTela
        se nenhuma vier no tempo."""
        # logger.debug(f'esperando: {nome}')
        nomes = (nome,) if isinstance(nome, str) else nome
        fim = time.monotonic() + timeout
        while time.monotonic() < fim:
            encontrada = self._achar_qualquer(nomes)[0]
            if encontrada is not None:
                # logger.debug('encontrada: '+str(encontrada))
                return encontrada
            self._dispensar_telas_caoticas()
            time.sleep(.25)
        raise ErroNaTela(f"'{nome}' nao apareceu em {timeout:.0f}s")

    def _clicar_enquanto_espera(self, alvo, botao_interstitial, timeout: float) -> None:
        logger.debug("_clicar_enquanto_espera: aguardando '%s' (interstitial '%s', timeout %.0fs)", alvo, botao_interstitial, timeout)
        fim = time.monotonic() + timeout
        while time.monotonic() < fim:
            if self._achar(alvo) is not None:
                logger.debug("_clicar_enquanto_espera: '%s' apareceu", alvo)
                return
            if self._achar(botao_interstitial) is not None:
                logger.debug("_clicar_enquanto_espera: clicando interstitial '%s'", botao_interstitial)
                self._clicar_imagem(botao_interstitial, 1)
        raise ErroNaTela(f"'{alvo}' nao apareceu em {timeout:.0f}s (mesmo clicando '{botao_interstitial}')")

    def _combo_enquanto_espera(self, alvo, combo, timeout: float) -> None:
        """Como _clicar_enquanto_espera, mas em vez de clicar numa imagem
        interstitial a cada volta, aperta 'combo' (tupla de teclas, repassada
        pra _combo) -- pra telas que avancam por atalho/combo de teclado
        em vez de um botao clicavel."""
        logger.debug("_combo_enquanto_espera: aguardando '%s' (combo %s, timeout %.0fs)", alvo, combo, timeout)
        fim = time.monotonic() + timeout
        while time.monotonic() < fim:
            if self._achar(alvo) is not None:
                logger.debug("_combo_enquanto_espera: '%s' apareceu", alvo)
                return
            self._combo(*combo)
        raise ErroNaTela(f"'{alvo}' nao apareceu em {timeout:.0f}s (mesmo com o combo '{combo}')")

    def _sumir(self, nome: str, timeout: float) -> None:
        """Espera a imagem DESAPARECER (ex: splash de carregamento)."""
        # logger.debug(f'esperando sumir: {nome}')
        fim = time.monotonic() + timeout
        while time.monotonic() < fim:
            self._dispensar_telas_caoticas()
            if self._achar(nome) is None:
                # logger.debug(f'    sumiu: {nome}')
                return
            time.sleep(self.pausa)
        raise ErroNaTela(f"'{nome}' nao sumiu em {timeout:.0f}s")

    def _sumir_com_tolerancia(self, nome: str, timeout: float, tolerancia_reaparicao: float) -> None:
        """Como _sumir, mas tolera ausência transitória -- necessário
        quando outro elemento de tela oclui a imagem momentaneamente
        (ex: um aviso de "aguarde" coberto por telas intermediárias
        durante um processo longo) sem que isso signifique que o
        processo terminou.

        Cada reaparecimento dentro de 'tolerancia_reaparicao' segundos
        reinicia o teto de 'timeout' -- só conclui desaparecimento
        definitivo após o período de tolerância inteiro transcorrer sem
        reaparecimento algum.
        """
        fim = time.monotonic() + timeout
        ausente_desde = None
        while time.monotonic() < fim:
            self._dispensar_telas_caoticas()
            if self._achar(nome) is None:
                if ausente_desde is None:
                    ausente_desde = time.monotonic()
                elif time.monotonic() - ausente_desde >= tolerancia_reaparicao:
                    return
            else:
                ausente_desde = None
                fim = time.monotonic() + timeout  # reapareceu -- reinicia o teto geral
            time.sleep(self.pausa)
        raise ErroNaTela(f"'{nome}' nao desapareceu definitivamente em {timeout:.0f}s")

    def _esperar_com_intermitencia(self, alvo, imagem_intermitente, teto: float, tolerancia_intermitencia: float) -> str:
        """Espera 'alvo' (imagem ou tupla) aparecer, usando o
        aparecimento intermitente de 'imagem_intermitente' como sinal de
        que o processo em andamento continua ativo -- não é a
        desaparição dela que importa, é a INTERMITÊNCIA em si: enquanto
        ela continuar surgindo de tempos em tempos, o processo está
        vivo. Se ela parar de surgir por mais de 'tolerancia_intermitencia'
        segundos sem 'alvo' ter aparecido, conclui que o processo travou
        e estoura ErroNaTela antes mesmo do teto geral -- em vez de uma
        espera cega até 'teto' esgotar. 'teto' é a rede de segurança
        final, caso nem 'alvo' nem 'imagem_intermitente' apareçam nunca.

        'alvo' pode ser None quando não há imagem de sucesso a esperar --
        nesse modo, a função só monitora a intermitência, e devolve None
        assim que ela parar de aparecer por 'tolerancia_intermitencia'
        segundos (esse é o desfecho NORMAL desse modo, não um erro).
        """
        fim = time.monotonic() + teto
        ultima_intermitencia = None  # ainda nao viu 'imagem_intermitente' nenhuma vez
        alvos = None if alvo is None else ((alvo,) if isinstance(alvo, str) else alvo)
        while time.monotonic() < fim:
            # logger.debug(f'loop _esperar_com_intermitencia, ultima: {ultima_intermitencia} - agora: {time.monotonic()}')
            if alvos is not None:
                encontrado = self._achar_qualquer(alvos)[0]
                if encontrado is not None:
                    # logger.debug(f'encontrado: {encontrado}')
                    return encontrado
            if self._achar(imagem_intermitente) is not None:
                # logger.debug(f'refresh {imagem_intermitente} - ultima: {ultima_intermitencia}')
                ultima_intermitencia = time.monotonic()
            elif ultima_intermitencia is not None and time.monotonic() - ultima_intermitencia >= tolerancia_intermitencia:
                if alvo is None:
                    return None
                raise ErroNaTela(f"'{imagem_intermitente}' parou de aparecer por {tolerancia_intermitencia:.0f}s -- processo parece travado")
            self._dispensar_telas_caoticas()
        raise ErroNaTela(f"'{alvo}' nao apareceu em {teto:.0f}s")

    def _visivel(self, nome, timeout: float = 0) -> bool:
        """Checa sem estourar -- para escolher caminhos (sucesso vs erro).
        'nome' pode ser uma imagem so ou uma tupla de imagens alternativas
        -- encontrar QUALQUER uma delas conta."""
        nomes = (nome,) if isinstance(nome, str) else nome
        fim = time.monotonic() + timeout
        while True:
            if any(self._achar(n) is not None for n in nomes):
                return True
            if time.monotonic() >= fim:
                return False

    def _visivel_estavel(self, nome, tempo_estavel: float) -> bool:
        """Checa se a imagem fica visível de forma CONTÍNUA por
        'tempo_estavel' segundos -- diferente de _visivel (que aceita o
        primeiro aparecimento, por mais breve que seja), isso descarta
        reconhecimento falso-positivo passageiro (ex: um frame de
        transição que casa com o template por acaso). Qualquer sumiço no
        meio do caminho já devolve False na hora, sem esperar o resto do
        tempo. Devolve True só se ficou visível o período inteiro.
        """
        fim = time.monotonic() + tempo_estavel
        while time.monotonic() < fim:
            if self._achar(nome) is None:
                return False
            time.sleep(self.pausa)
        return True

    def detectar_etapa(self, *imagens, timeout: float) -> int:
        """Recebe imagens-pivo EM ORDEM de avanco no fluxo e retorna o
        indice da mais adiantada ja visivel agora, ou -1 se nenhuma.
        Permite 'acoplar' o robo a qualquer ponto do fluxo real, em vez de
        assumir que sempre comeca do zero -- necessario quando o app alvo
        e o robo tem inicializacao independente (uma etapa pode ja ter
        vindo e sumido antes do script comecar a olhar).

        Cada 'imagem' e uma imagem so ou uma tupla de imagens alternativas
        (mesmo pivo alcancavel por mais de uma tela) -- ver _visivel. E
        checada com 'timeout', nao um unico _achar instantaneo -- testa
        cedo, falha rapido: uma renderizacao ainda em andamento nao deve
        ser confundida com 'essa etapa nao foi alcancada'. 'timeout' curto
        de proposito.
        """
        etapa_atual = -1
        for indice, nome in enumerate(imagens):
            visivel = self._visivel(nome, timeout=timeout)
            logger.debug("detectar_etapa[%s] %s -> %s", indice, nome, "visivel" if visivel else "nao visivel")
            if visivel:
                etapa_atual = indice
        return etapa_atual

    def avancar(self, etapas, timeout_deteccao: float, se_nenhum_pivo=None) -> int:
        """etapas: sequencia ordenada de (pivo, *acoes) -- pivo prova que a
        etapa foi alcancada (a tela correspondente esta na frente AGORA),
        cada acao (recebe so a Tela) e a resposta a dar POR CAUSA de estar
        vendo esse pivo -- ex: (IMG_LOGIN, login(...)): ve o login, entao
        faz login. Detecta a etapa mais avancada ja alcancada e executa as
        acoes dela em diante, na ordem declarada -- so avanca, nao ha
        'retroceder'. Nao encontrar nenhum pivo (-1) roda a sequencia
        inteira do inicio. 'Acopla' o robo em qualquer ponto de uma
        sequencia de qualquer tamanho, sem indices/contadores manuais no
        chamador. Devolve o indice detectado, pro chamador decidir algo
        com essa informacao (ex: Processo.inicializar decidindo se abre
        uma instancia nova do app).

        'se_nenhum_pivo': callable sem argumento, chamado SO quando nenhum
        pivo foi encontrado (indice == -1) -- ANTES de rodar a sequencia de
        acoes, nao depois (a primeira acao pode depender disso ja ter
        acontecido, ex: abrir o app antes de esperar a tela de login dele).
        Depois dele NAO se re-detecta: logo apos abrir, alguns pivos mais
        adiantados (ex: icone do app na barra de tarefas) ja aparecem antes
        das telas iniciais -- uma segunda deteccao pularia etapas que ainda
        vao acontecer.

        Se alguma acao especifica precisar de dados extras (ex: login
        precisa de credenciais), o lambda do chamador captura isso do
        proprio escopo -- avancar() nao carrega nada que so uma etapa usa.
        """
        pivos = [pivo for pivo, *_ in etapas]
        indice = self.detectar_etapa(*pivos, timeout=timeout_deteccao)
        logger.info(f'Detectado etapa índice: {indice}')

        if indice == -1 and se_nenhum_pivo is not None:
            logger.info("avancar: nenhum pivo -- chamando se_nenhum_pivo()")
            se_nenhum_pivo()

        inicio = max(indice, 0)
        logger.info("avancar: rodando a partir da etapa %s de %s", inicio, len(etapas))
        for indice_etapa, (pivo, *acoes) in enumerate(etapas[inicio:], start=inicio):
            for indice_acao, acao in enumerate(acoes):
                logger.debug("avancar: etapa %s (pivo=%s), acao %s -- iniciando", indice_etapa, pivo, indice_acao)
                acao(self)
                logger.debug("avancar: etapa %s, acao %s -- concluida", indice_etapa, indice_acao)

        return indice

    def _clicar_imagem(self, nome, timeout: float, offset_h: int = 0, offset_v: int = 0) -> None:
        """'nome' pode ser uma imagem so ou uma tupla de imagens
        alternativas -- clica na primeira que for encontrada."""
        self._esperar(nome, timeout)
        nomes = (nome,) if isinstance(nome, str) else nome
        _, pos = self._achar_qualquer(nomes)
        if pos is None:
            logger.info(f"'{nome}' sumiu entre a espera e o clique")
            return
        pyautogui.click(pos.x + offset_h, pos.y + offset_v)
        time.sleep(self.pausa)

    def _clicar_similares(self, *imagens, timeout: float, repetir: int = 1) -> None:
        """Clica na primeira das imagens que aparecer. Todas sao procuradas
        juntas a cada volta de polling (A, B, A, B... sem esperar uma esgotar
        o tempo antes de olhar a outra), dentro de um unico teto 'timeout'.
        'repetir' refaz essa espera inteira, com teto novo, ate esse numero
        de vezes; esgotando, relanca o ErroNaTela da ultima tentativa.
        """
        ultimo_erro = None
        for tentativa in range(1, repetir + 1):
            logger.debug("_clicar_similares: tentativa %s/%s, procurando %s (timeout %.0fs)", tentativa, repetir, imagens, timeout)
            try:
                self._clicar_imagem(imagens, timeout)
                return
            except ErroNaTela as erro:
                ultimo_erro = erro
        raise ultimo_erro


    def _digitar(self, texto: str, intervalo: float = None) -> None:
        intervalo = self.intervalo if intervalo is None else intervalo
        pyautogui.write(str(texto), interval=intervalo)

    def _digitar_unicode(self, texto: str, intervalo: float = None) -> None:
        """Como '_digitar', mas usando SendInput + KEYEVENTF_UNICODE em vez
        de pyautogui.write() -- cobre acentuacao (ex: 'Ç'), que o mapeamento
        de tecla virtual do pyautogui nao cobre. Dispara um evento de tecla
        por caractere, igual digitacao normal (campos que filtram uma lista
        conforme voce digita dependem disso)."""
        intervalo = self.intervalo if intervalo is None else intervalo
        extra = ctypes.pointer(ctypes.c_ulong(0))
        for caractere in str(texto):
            codigo = ord(caractere)
            keyDown = _Input(_INPUT_KEYBOARD, _InputUniao(_KeyBdInput(0, codigo, _KEYEVENTF_UNICODE, 0, extra)))
            enviados = ctypes.windll.user32.SendInput(1, ctypes.pointer(keyDown), ctypes.sizeof(keyDown))
            if enviados != 1:
                logger.warning(f"SendInput rejeitou o caractere '{caractere}' (codigo {codigo})")
            keyRelease = _Input(_INPUT_KEYBOARD, _InputUniao(_KeyBdInput(0, codigo, _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP, 0, extra)))
            ctypes.windll.user32.SendInput(1, ctypes.pointer(keyRelease), ctypes.sizeof(keyRelease))
            time.sleep(intervalo)

    def _atalho(self, *tecla: str) -> None:
        pyautogui.hotkey(*tecla)
        time.sleep(self.pausa)

    def _combo(self, *sequencia, repetir: int = 1, intervalo: float = None) -> None:
        """Aperta uma sequencia de teclas, em ordem. Cada item e uma tecla
        so ("enter") ou uma combinacao ("alt", "e") como tupla. 'repetir'
        refaz a sequencia inteira esse numero de vezes. 'intervalo' e a
        pausa entre cada tecla -- por padrao usa self.pausa (nao da pra
        referenciar self direto no valor padrao do parametro: ele e
        calculado uma vez, quando a classe e carregada, antes de existir
        qualquer instancia).
        """
        intervalo = self.pausa if intervalo is None else intervalo
        for _ in range(repetir):
            for tecla in sequencia:
                if isinstance(tecla, str):
                    pyautogui.press(tecla)
                else:
                    pyautogui.hotkey(*tecla)
            time.sleep(intervalo)

    def inicializacao_geral(self):
        self._atalho(("win", "d")) # minimiza tudo, pra "limpar o ambiente"
        time.sleep(10)
        try: 
            self._clicar_similares(img.IMG_APPCONTROLLER_MINIMIZADO_SINALIZANDO, img.IMG_SISTEMANFSE_EXE_MINIMIZADO, timeout=self.timeouts["erro_sistemanfse.exe"], repetir=3)
        except:
            pass
        logger.info("aguardando erro \"SISTEMAnfse.exe\" [%ss]", self.timeouts["erro_sistemanfse.exe"])
        self._clicar_similares(img.IMG_WIN_NAO_PODE_ENCONTRAR_SISTEMANFSE_EXE, img.IMG_WIN_NAO_PODE_ENCONTRAR_SISTEMA_EXE, timeout=self.timeouts["erro_sistemanfse.exe"])
        self._atalho('enter')

    def EJECTION(self) -> None:
        """O NUKE. So roda quando um erro fatal escapou ate o topo do
        processo -- mata o app inteiro na marra (nao so a janela: o
        processo), pra garantir que a proxima execucao comece de uma
        maquina limpa, sem instancia velha/travada pendurada.
        """
        logger.info("EJECTION: taskkill /IM AppController.exe")
        subprocess.run(["taskkill", "/F", "/IM", "AppController.exe"], capture_output=True)

    def recuperar_para_pivo(self, timeout: float) -> None:
        """Pivo: o estado absorvente sob a operacao ESC -- aplicar ESC nele
        nao produz transicao. Qualquer pilha de avisos/dialogos abertos:
        ESC sempre fecha o topo. Logo, para uma pilha de profundidade finita
        e desconhecida d, uma sequencia de N >= d aplicacoes de ESC converge
        ao pivo, sem nunca precisar conhecer d. Este metodo emite ESC dentro
        do orcamento de tempo 'timeout' (nao uma contagem fixa de tentativas)
        e verifica a cada volta se o pivo foi reconhecido.

        Nao reconhecer o pivo dentro do timeout estoura ErroNaTela -- quem
        decide o resto e o chamador (tipicamente escala para EJECTION()).
        """
        fim = time.monotonic() + timeout
        while time.monotonic() < fim:
            for _ in range(3):
                self._combo("esc", repetir=2, intervalo=.5)
                self._clicar_imagem(img.IMG_PIVO_TELA, offset_v=15, timeout=10)
                
            if self._achar(img.IMG_DESEJA_SAIR_DO_PROGRAMA) is not None:
                self._atalho('enter') # Não para "Sair do programa"
                logger.info("pivo reconhecido")
                return
            time.sleep(self.pausa)
        raise ErroNaTela(f"nao reconheceu o pivo nem apos {timeout}s de ESC repetidos")


    # ===================== Suas acoes especificas ===================== #
    # A partir daqui entram os metodos de negocio do SEU fluxo (ex: logar,
    # navegar ate a tela certa, preencher um formulario, confirmar um
    # envio) -- cada um montado em cima do motor acima. Nenhum decide o
    # que fazer com o resultado: quem decide e o Processo.

    def login(self, passw):
        self._esperar(img.IMG_LOGIN, 10)
        self._clicar_imagem(img.IMG_LOGIN_CAMPO_EMPRESA, 1)
        self._combo("1", "tab", "tab", *"T.I", "tab", *passw, ("alt", "o"))

    def reposicionar_para_proximo_lote(self):
        logger.debug('reposicionar_para_proximo_lote')
        self._clicar_imagem(img.IMG_XML_DE_ENVIO, offset_v=-35, timeout=2)
        self._combo(('shift', 'tab'))

    def sair_simbolus(self) -> None:
        """Sai do SIMBOLUS (mata o app inteiro, segundo o usuario) --
        chamado ao final de cada ciclo de fase, sucesso ou nao."""

        self._combo_enquanto_espera(img.IMG_MENU_LIMPO, ("esc",), timeout=15)
        if self._achar(img.IMG_MENU_LIMPO):
            self._combo("alt", "left", "up", "up", "enter")
            self._achar(img.IMG_DESEJA_SAIR_DO_PROGRAMA)
            self._combo("tab", "enter")
            time.sleep(3)
        else:
            raise ErroNaTela('Não foi possível realizar saída do sistema', print=True)
            

