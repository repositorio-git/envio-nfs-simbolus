"""Parametros num lugar so. Nada de timeout/caminho chumbado no meio do codigo.

Senhas NAO ficam aqui -- vem do .env (ver tarefas.py). Aqui so o que nao e
segredo.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    # Quanto o robo espera cada coisa acontecer, em segundos. Os nomes
    # abaixo sao so exemplo (splash/login) -- troque pelos nomes reais das
    # etapas do SEU fluxo de inicializacao.
    "timeouts": {
        "erro_sistemanfse.exe": 10,
        "rel_estouro_estoque_minimo": 10,
        "login_aparecer": 30,
        "pos_login": 30,
        "deteccao_etapa": .5,   # timeout curto por imagem-pivo ao "acoplar" -- testa cedo, falha rapido
        "recuperacao_pivo": 15,  # segundos de recuperacao repetida, ate reconhecer o pivo
        "carregamento_simbolus": 300, # principal demora no carregamento desse fluxo, 5 minutos, após login.
        "teto_menu_principal": 390,  # 6 minutos e meio - _clicar_enquanto_espera chegar no IMG_MENU
        "clicar_alterar": 3,  # botao "Alterar" na tela do RPS selecionado
        "aguardar_transmissao": 30,
        "teto_transmissao_lote": 300,  # espera maxima pela transmissao de UM lote inteiro (rede de seguranca)
        "rodape_estavel_transmissao": 3,  # rodape da tela de notas visivel sem piscar por isso = lote processado  # Após clicar no botão "Transmitir" até aparecer algum resultado: "sucesso" ou "!"
        "aguardar_carregamento_pos_exibir": 60,
        "aguardar_geracao_lote": 180
    },

    # Quantas vezes tentar uma FASE INTEIRA (Processo._rodar_fase) apos um
    # erro fatal -- cada tentativa falha aciona EJECTION() (mata o app a
    # forca) e recomeca a fase do zero (reinicializa, reconsulta tudo).
    # Esgotando isso, relanca a excecao pro agendador externo decidir.
    "max_tentativas_fase": 3,

    # Fase 1 -- RF-12: um grupo por tipo de conta, na ORDEM em que devem
    # ser processados. Valores herdados do robo Rocketbot anterior
    # (Documentacao Tecnica v3, secao 3.3), conferidos contra a tela real
    # "Contas a Receber" do SIMBOLUS em 2026-10-30. Quando "filtrar_por_periodo"
    # e "Pagamento", o bloco "Status" da tela trava sozinho em "Pagos"
    # (nao da pra escolher outro); so com "Vencimento" o Status fica
    # selecionavel de verdade.
    "grupos_conta": (
        {
            "tipo_conta": "MANUTENCAO",
            "conta": "MANUTENÇÃO",
            "filtrar_por_periodo": "Pagamento",
            "status": "Pagos",
            "notas_fiscais": "SEM NF EMITIDA",
        },
        {
            "tipo_conta": "SEPULTAMENTO",
            "conta": "VENDA DE SERVIÇOS - SEPULTAMENTO",
            "filtrar_por_periodo": "Pagamento",
            "status": "Pagos",
            "notas_fiscais": "SEM NF EMITIDA",
        },
        {
            "tipo_conta": "LAPIDE",
            "conta": "VENDA DE SERVIÇOS - LAPIDES",
            "filtrar_por_periodo": "Pagamento",
            "status": "Pagos",
            "notas_fiscais": "SEM NF EMITIDA",
        },
        {
            "tipo_conta": "JAZIGOS",
            "conta": "VENDA DE JAZIGOS",
            "filtrar_por_periodo": "Vencimento",
            "status": "Todos",
            "notas_fiscais": "SEM NF EMITIDA",
        },
    ),

    # Reconhecimento de imagem (PyAutoGUI).
    "confidence": .90,          # ajuste com o testar_imagem.py se precisar
    "intervalo_digitacao": .02,
    "pausa": .35,                # respiro depois de cada acao

    "caminhos": {
        "imagens": os.path.join(BASE_DIR, "paginas", "imagens"),
        "logs": os.path.join(BASE_DIR, "logs"),
    },

    # Senha (SMTP_SENHA) vem do .env -- host/porta/remetente nao sao segredo.
    "email": {
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "remetente": "cortex@cortel.com.br",
        "destinatarios_relatorio": [
            "rafael.dunker@cortel.com.br",
            "lucas.alves@cortel.com.br",
        ],
    },

}
