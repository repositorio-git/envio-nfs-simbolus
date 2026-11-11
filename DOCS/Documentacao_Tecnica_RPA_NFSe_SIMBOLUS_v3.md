**DOC. TÉCNICA --- RPA**

  --------------------- -------------------------------------------------
  **Documento:**        SIMBOLUS_NFSE -- RPA Geração e Envio de NFS-e no
                        SIMBOLUS

  **Solicitante:**      TI Cortel (melhoria interna --- descontinuação do
                        Rocketbot)

  **Responsável:**      Dunker
  --------------------- -------------------------------------------------

**PARTE 1 --- DOCUMENTAÇÃO TÉCNICA DO DESENVOLVIMENTO**

*1 Lógica de Negócio e Fluxo de Dados*

## **1.1 Regras de Negócio Aplicadas no Robô**

-   O robô opera exclusivamente via interface gráfica do SIMBOLUS (UI
    automation) --- não há acesso direto a banco de dados.

-   Fase 1 gera lotes de RPS para 4 tipos de conta, cada um com
    critérios de filtro distintos: Manutenção, Sepultamento e Lápide
    filtram por Pagamento / Pagos / SEM NF EMITIDA; Jazigos filtra por
    Vencimento / Abertos-Todos / SEM NF EMITIDA.

-   O período aplicado em todos os grupos é sempre do dia 01 do mês
    corrente até a data de execução.

-   Os números de RPS gerados são capturados via OCR (api.ocr.space) do
    popup \'Lote RPS Gerado com sucesso\' e acumulados no array, que é
    compartilhado entre as duas fases.

-   Fase 2 percorre o array e, para cada RPS, localiza o lote na tela
    NFS-e, altera as datas das até 10 notas permitidas por lote e
    transmite para a prefeitura.

-   Erros de transmissão são tratados individualmente: erro IBGE gera
    notificação imediata; lote não transmitido gera screenshot da aba
    Log + notificação; ao atingir 5 erros consecutivos a execução é
    interrompida e a equipe é notificada.

## **1.2 Principais Funções/Módulos do Código**

  --------------------------------------------------------------------------------------------------------------
  **Robô / Módulo**          **Recebe**     **Processa**               **Retorna / Produz**
  -------------------------- -------------- -------------------------- -----------------------------------------
  SIMBOLUS                   Credenciais    Abre o SIMBOLUS via        Tela Contas a Receber posicionada e
                             (TI CORTEL /   app.bat, faz login e       pronta para geração
                             514020)        navega até a tela Contas a 
                                            Receber                    

  SIMBOLUS_NFSe_GERA_LOTES   Tela Contas a  Executa 4 grupos de filtro array com todos os números de RPS
                             Receber aberta sequenciais → aciona botão gerados + e-mail de backup
                                            NFS-e → captura popup via  
                                            screenshot → OCR           
                                            (api.ocr.space) → extrai   
                                            RPS via script Python      
                                            (regex/ast)                

  SIMBOLUS_ENVIO_NFSE        array de RPS   Abre o SIMBOLUS via        Lotes transmitidos à prefeitura + e-mails
                             gerados        app_nfse.bat, faz login,   de status + array_lote_erro
                                            navega até tela NFS-e →    
                                            para cada RPS: localiza    
                                            lote, altera datas,        
                                            transmite, verifica        
                                            resultado e trata erros    
                                            (IBGE / lote_ok /          
                                            count_erro)                

  execScriptPython --- OCR   Janela de      pyautogui.screenshot() +   Números de RPS adicionados ao array
                             popup ativa    win32gui → POST para       
                             (foreground)   api.ocr.space → regex/ast  
                                            parseia retorno JSON e     
                                            extrai números de RPS      

  execScriptPython ---       Tela NFS-e com pyautogui.screenshot() +   C:\\CorteX\\SIMBOLUS\\LOTE_COM_ERRO.png
  Screenshot de erro         aba Log        win32gui → salva arquivo   (enviado como anexo no e-mail de erro)
                             visível        em disco                   
  --------------------------------------------------------------------------------------------------------------

## **1.3 Fluxo de Dados**

-   Entrada: data corrente (gerada em runtime). Credenciais do SIMBOLUS
    (Empresa 1 / TI CORTEL / 514020). Chave API OCR.space
    (K89012960388957, hardcoded no execScriptPython).

-   Processamento Fase 1: tela Contas a Receber → filtros por tipo de
    conta → botão NFS-e → popup com RPS gerados → OCR → array acumulado.

-   Processamento Fase 2: para cada RPS do array → tela NFS-e → localiza
    lote → altera datas das notas → transmite → verifica retorno da
    prefeitura.

-   Saída: lotes transmitidos à prefeitura. E-mails de backup, erros e
    conclusão. Screenshots dos popups
    (SIMBOLUS_MANUT/SEPULT/LAPIDE/JAZIGOS.png --- sobrescritos a cada
    execução). Screenshot de erro (LOTE_COM_ERRO.png --- sobrescrito a
    cada ocorrência).

*2 Especificação Técnica (o que foi construído)*

## **2.1 Detalhamento**

**Onde roda (servidor/máquina):** 10.1.253.55 --- sessão RDP interativa,
usuário MATRIZ\\CORTEX.

**Sistemas/sites acessados**

  ------------------------------------------------------------------------
  **Sistema /      **Credencial usada       **Observação**
  site**           (nome, nunca a senha)**  
  ---------------- ------------------------ ------------------------------
  SIMBOLUS ---     Empresa 1 / Usuário TI   Tela Contas a Receber --- Fase
  app.bat          CORTEL                   1 (geração)

  SIMBOLUS ---     Empresa 1 / Usuário TI   Tela NFS-e --- Fase 2 (envio)
  app_nfse.bat     CORTEL                   

  api.ocr.space    Chave K89012960388957    OCR dos popups de RPS gerados
                   (hardcoded no script     --- engine 2 para MANUT,
                   Python)                  engine 1 para demais

  Outlook365       cortex@cortel.com.br     Envio de todos os e-mails de
                   (módulo nativo do        notificação
                   Rocketbot)               
  ------------------------------------------------------------------------

**Passos principais do robô**

  -----------------------------------------------------------------------------
  **Ordem**   **Ação**                       **O que produz como saída**
  ----------- ------------------------------ ----------------------------------
  1           SIMBOLUS: login via app.bat +  Tela Contas a Receber posicionada
              navegação até Contas a Receber 

  2           GERA_LOTES grupo 1: filtro     RPS de manutenção adicionados ao
              MANUTENÇÃO → NFS-e → OCR       array

  3           GERA_LOTES grupo 2: filtro     RPS de sepultamento adicionados ao
              SEPULTAMENTO → NFS-e → OCR     array

  4           GERA_LOTES grupo 3: filtro     RPS de lápide adicionados ao array
              LÁPIDE → NFS-e → OCR           

  5           GERA_LOTES grupo 4: filtro     RPS de jazigos adicionados ao
              JAZIGOS → NFS-e → OCR          array

  6           E-mail de backup do array +    E-mail enviado para rafael.dunker
              chamada SIMBOLUS_ENVIO_NFSE    e lucas.alves --- Fase 2 iniciada

  7           ENVIO_NFSE: login via          Tela NFS-e posicionada
              app_nfse.bat + navegação até   
              tela NFS-e                     

  8           ENVIO_NFSE: loop --- localiza  Lotes transmitidos ou registrados
              cada RPS, altera datas das     em array_lote_erro
              notas do lote, transmite       

  9           E-mail de lotes não            Execução encerrada, equipe
              transmitidos + e-mail de       notificada
              conclusão                      
  -----------------------------------------------------------------------------

**Dependências:** Rocketbot com módulos Outlook365, Files, Keyboard\_.
Python com PyAutoGUI e win32gui (via execScriptPython do Rocketbot). API
externa OCR.space. Sem acesso a banco de dados --- toda interação via
interface gráfica (UI automation).

## **2.2 Interfaces**

Não há relatórios ou arquivos de saída entregues diretamente ao usuário
final além dos e-mails de notificação. Os screenshots dos popups de
geração (SIMBOLUS_MANUT.png, SIMBOLUS_SEPULT.png, SIMBOLUS_LAPIDE.png,
SIMBOLUS_JAZIGOS.png) são arquivos internos, sobrescritos a cada
execução. O arquivo LOTE_COM_ERRO.png é gerado a cada lote com falha de
transmissão, sobrescrito na próxima ocorrência, e enviado como anexo no
e-mail de notificação correspondente.

## **2.3 Aspectos Críticos ou Relevantes**

-   Toda a automação depende da interface gráfica do SIMBOLUS ---
    qualquer alteração de layout, posição de campos, ordem de itens em
    dropdowns ou texto de popups quebra o robô sem aviso prévio.

-   A seleção da conta no dropdown é feita por posição (ordem dos itens
    na lista) --- se o SIMBOLUS alterar a ordem das contas, o robô
    selecionará a errada silenciosamente.

-   O OCR depende de API externa (ocr.space) --- indisponibilidade ou
    retorno incorreto resulta em array vazio e Fase 2 sem itens para
    transmitir.

-   A busca do lote na Fase 2 percorre até 10 posições na grid. RPS cujo
    lote esteja além da décima posição não será localizado e irá direto
    para o array_lote_erro.

-   A sessão RDP (10.1.253.55) deve estar ativa e com tela desbloqueada
    no horário de execução --- PyAutoGUI e clickimage do Rocketbot não
    funcionam sem sessão gráfica interativa ativa (Sessão 0 não tem
    desktop visível).

-   Resolução e escala de DPI da sessão devem ser estáveis --- o
    reconhecimento de imagem do Rocketbot (clickimage/waitimage) opera
    por casamento de pixels.

## **2.4 Política de Carga / Agendamento**

Task Scheduler do Windows: task RPA_SIMBOLUS_MANUT, pasta \\RPA_CORTEL,
disparo diário às 16:00, configurada como \'Executar somente quando o
usuário estiver conectado\', usuário MATRIZ\\CORTEX. Não há reexecução
automática em caso de falha --- reprocessamento deve ser acionado
manualmente.

## **2.5 Homologação / Validação**

  ------------------------------------------------------------------------------------
  **Código do **Tipo**           **Solicitante**   **Responsável**   **Data da
  chamado**                                                          validação**
  ----------- ------------------ ----------------- ----------------- -----------------
  ---         Produção ---       TI Cortel         Dunker            A preencher após
              migração de                                            validação em
              plataforma                                             Python
              (Rocketbot →                                           
              Python)                                                

  ------------------------------------------------------------------------------------

*3 Cronograma Macro de Atividades*

  -----------------------------------------------------------------------------------
  **Atividade**            **Início     **Término    **Responsável**   **Término
                           previsto**   previsto**                     realizado**
  ------------------------ ------------ ------------ ----------------- --------------
  Levantamento e           ---          ---          Dunker            28/08/2026
  documentação AS-IS                                                   
  (Rocketbot)                                                          

  Desenvolvimento Python   31/08        A definir    A definir         ---
  --- Fase 1 (geração +                                                
  OCR)                                                                 

  Desenvolvimento Python   A definir    A definir    A definir         ---
  --- Fase 2 (envio +                                                  
  tratamento de erros)                                                 

  Homologação em produção  A definir    A definir    A definir         ---
  --- Fase 1                                                           

  Homologação em produção  A definir    A definir    A definir         ---
  --- Fase 2                                                           

  Desativação do Rocketbot A definir    A definir    A definir         ---
  / entrada em produção                                                
  Python                                                               
  -----------------------------------------------------------------------------------

**PARTE 2 --- MANUAL DE PASSAGEM, NÍVEL 1**

**Sintomas comuns**

-   Robô não rodou às 16h (task desabilitada, servidor reiniciou ou
    sessão estava bloqueada).

-   Robô rodou mas não completou --- e-mail de conclusão não chegou.

-   E-mail de backup do array chegou vazio ou sem números de RPS (OCR
    falhou na Fase 1).

-   E-mail de interrupção por 5 erros consecutivos --- transmissão parou
    no meio da Fase 2.

-   E-mail de lotes não transmitidos chegou com itens --- alguns lotes
    não foram enviados à prefeitura.

**O que o Nível 1 pode checar**

-   Task RPA_SIMBOLUS_MANUT está habilitada no Agendador de Tarefas do
    servidor 10.1.253.55.

-   A sessão RDP está aberta e com tela desbloqueada.

-   O SIMBOLUS está acessível --- abrir app.bat manualmente e confirmar
    tela de login.

-   Os e-mails de notificação chegaram na caixa de
    contasareceber@cortel.com.br.

-   O log do Rocketbot mostra mensagem de erro (verificar via interface
    do Rocketbot ou na pasta C:\\CorteX\\CORTEL_RS\\).

**O que o Nível 1 pode fazer sozinho**

-   Disparar execução manual via Task Scheduler (botão direito →
    Executar na task RPA_SIMBOLUS_MANUT).

-   Confirmar se o SIMBOLUS está no ar --- abrir app.bat manualmente e
    verificar tela de login.

-   Confirmar se a api.ocr.space está respondendo --- acessar
    https://ocr.space no navegador do servidor.

**Escalar pro desenvolvedor quando:** o erro está na lógica do robô
(campo não encontrado, reconhecimento de imagem falhou, loop não
encerrou), o SIMBOLUS mudou de layout ou ordem de campos, ou o OCR
retorna resultados inconsistentes de forma repetida.

**Levar para o desenvolvedor:** trecho do log do Rocketbot com o erro e
horário da execução. Informação sobre qual fase falhou (geração ou
envio) e qual foi o último e-mail de notificação recebido. Screenshots
disponíveis em C:\\CorteX\\SIMBOLUS\\ (se existirem da execução com
falha).

*--- Fim do documento ---*
