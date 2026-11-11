**1Especificação Técnica de RPA**

**Geração e Envio Automatizado de NFS-e no SIMBOLUS**

*Memorial Parque Jardim dos Girassóis*

Cortel --- Setor de Tecnologia da Informação

  -----------------------------------------------------------------------
  **Projeto**           RPA --- NFS-e SIMBOLUS
  --------------------- -------------------------------------------------
  **Demandante**        Cortel --- TI (melhoria interna ---
                        descontinuação do Rocketbot)

  **Responsável         Dunker
  funcional**           

  **Plataforma atual**  Rocketbot + Python (PyAutoGUI, win32gui,
                        OCR.space)

  **Servidor**          10.1.253.55 --- Sessão RDP dedicada

  **Agendamento**       Task Scheduler --- RPA_SIMBOLUS_MANUT --- Diário
                        às 16:00
  -----------------------------------------------------------------------

# **1. Visão geral**

Este documento descreve o processo automatizado de geração e envio de
Notas Fiscais de Serviço Eletrônicas (NFS-e) no sistema SIMBOLUS,
operado pelo Memorial Parque Jardim dos Girassóis. A automação é
executada inteiramente via interface gráfica (UI automation) do
SIMBOLUS, sem acesso direto a banco de dados.

## **1.1 Objetivo**

-   Eliminar a necessidade de operador humano executar manualmente, às
    16h, a geração de lotes de RPS e a transmissão das NFS-e para a
    prefeitura.

-   Padronizar o procedimento de geração de lotes entre os 4 tipos de
    conta (Manutenção, Sepultamento, Lápide, Jazigos).

-   Notificar a área de Contas a Receber sobre o resultado da execução
    via e-mail.

## **1.2 Escopo**

Estão no escopo deste documento os seguintes robôs e fases:

  ---------------------------------------------------------------------------
  **Fase**   **Robôs**                  **Descrição**
  ---------- -------------------------- -------------------------------------
  Fase 1 --- SIMBOLUS →                 Login no SIMBOLUS, navegação até
  Geração    SIMBOLUS_NFSe_GERA_LOTES   Contas a Receber, execução dos 4
                                        grupos de filtro, geração dos lotes
                                        via botão NFS-e, captura dos RPS
                                        gerados e acúmulo no array

  Fase 2 --- SIMBOLUS_ENVIO_NFSE        Login no SIMBOLUS em modo NFS-e,
  Envio                                 navegação até a tela Nota Fiscal de
                                        Serviço Eletrônica, transmissão de
                                        cada lote do array, tratamento de
                                        erros e notificação por e-mail
  ---------------------------------------------------------------------------

## **1.3 Fora do escopo**

-   Envio assistido de manutenção --- SIMBOLUS_ENVIO_ASSISTIDO_MANUT.

-   Ajuste de datas em lotes existentes --- SIMBOLUS_AJUSTA_DATAS.

-   Reenvio manual de lotes com erro --- SIMBOLUS_REENVIO_LOTES.

-   Tratamento ou correção dos erros retornados pela prefeitura
    (responsabilidade da área financeira).

# **2. Arquitetura da solução**

## **2.1 Estrutura no Rocketbot**

A solução é composta por 6 robôs no arquivo SIMBOLUS_NFSE.db, em
C:\\CorteX\\CORTEL_RS\\. Os robôs no escopo são encadeados
sequencialmente via execRocketBotDB. Os robôs fora do escopo
(SIMBOLUS_AJUSTA_DATAS, SIMBOLUS_REENVIO_LOTES, SIMBOLUS_LOGIN_ENVIO)
não fazem parte do fluxo de produção diária descrito neste documento.

  ---------------------------------------------------------------------------------------
  **Robô**                   **Função**     **Chama**                        **Escopo**
  -------------------------- -------------- -------------------------------- ------------
  SIMBOLUS                   Ponto de       SIMBOLUS_NFSe_GERA_LOTES         ✓ Dentro
                             entrada                                         
                             (geração).                                      
                             Login no                                        
                             SIMBOLUS,                                       
                             navegação até                                   
                             Contas a                                        
                             Receber                                         

  SIMBOLUS_NFSe_GERA_LOTES   4 grupos de    SIMBOLUS_ENVIO_NFSE              ✓ Dentro
                             filtro                                          
                             sequenciais,                                    
                             geração dos                                     
                             lotes via                                       
                             botão NFS-e,                                    
                             captura dos                                     
                             RPS via OCR,                                    
                             acúmulo no                                      
                             array                                           

  SIMBOLUS_ENVIO_NFSE        Login no       (fim do fluxo)                   ✓ Dentro
                             SIMBOLUS em                                     
                             modo NFS-e,                                     
                             navegação até                                   
                             a tela NFS-e,                                   
                             transmissão de                                  
                             cada lote do                                    
                             array                                           

  SIMBOLUS_LOGIN_ENVIO       Ponto de       SIMBOLUS_ENVIO_ASSISTIDO_MANUT   ✗ Fora
                             entrada                                         
                             alternativo                                     
                             para envio                                      
                             assistido                                       

  SIMBOLUS_AJUSTA_DATAS      Ajuste manual  (fim do fluxo)                   ✗ Fora
                             de datas em                                     
                             RPS existentes                                  

  SIMBOLUS_REENVIO_LOTES     Reenvio manual (fim do fluxo)                   ✗ Fora
                             de lotes com                                    
                             erro                                            
  ---------------------------------------------------------------------------------------

## **2.2 Orquestração**

-   Disparo: Task Scheduler do Windows (RPA_SIMBOLUS_MANUT), pasta
    \\RPA_CORTEL, diário às 16:00, usuário MATRIZ\\CORTEX.

-   Sessão: Estação 10.1.253.55 via RDP, sessão interativa ativa e com
    tela desbloqueada (obrigatório para PyAutoGUI e clickimage do
    Rocketbot funcionarem).

-   Credenciais SIMBOLUS: Empresa 1, Usuário TI CORTEL, Senha 514020.

-   E-mail: Outlook365 (cortex@cortel.com.br), módulo nativo do
    Rocketbot.

## **2.3 Ambiente de execução**

  -----------------------------------------------------------------------
  **Item**              **Configuração**
  --------------------- -------------------------------------------------
  Servidor              10.1.253.55 --- Sessão Windows dedicada

  Usuário Windows       MATRIZ\\CORTEX

  Usuário SIMBOLUS      TI CORTEL

  Sessão                RDP interativa, tela desbloqueada, resolução fixa

  Rocketbot DB          C:\\CorteX\\CORTEL_RS\\SIMBOLUS_NFSE.db
  -----------------------------------------------------------------------

## **2.4 Dependências externas**

-   SIMBOLUS (SIMB Sistemas) --- aplicação desktop Windows.

-   app.bat ---
    \\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\app.bat (Fase 1).

-   app_nfse.bat ---
    \\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\app_nfse.bat (Fase
    2).

-   API OCR.space (chave K89012960388957) --- leitura dos popups de RPS
    gerados.

-   PyAutoGUI e win32gui --- screenshots e foco de janela (via
    execScriptPython do Rocketbot).

-   Outlook365 --- módulo Rocketbot para envio de e-mails.

# **3. Fluxo principal de execução**

## **3.1 Visão de alto nível**

-   Fase 1 --- Geração: o robô SIMBOLUS abre o sistema, faz login e
    navega até a tela Contas a Receber. O robô SIMBOLUS_NFSe_GERA_LOTES
    percorre sequencialmente os 4 tipos de conta, aplica os filtros
    correspondentes, aciona o botão NFS-e e aguarda o popup \'Lote RPS
    Gerado com sucesso\'. Faz OCR do popup para extrair os números de
    RPS e os acumula no array. Ao final, envia e-mail de backup do array
    e chama SIMBOLUS_ENVIO_NFSE.

-   Fase 2 --- Envio: o robô SIMBOLUS_ENVIO_NFSE abre o sistema em modo
    NFS-e, faz login e navega até a tela Nota Fiscal de Serviço
    Eletrônica. Para cada RPS no array, localiza o lote, preenche a data
    do dia e transmite para a prefeitura. Trata erros individualmente
    (IBGE, lote não transmitido, 5 erros consecutivos) com notificação
    por e-mail. Ao final, envia e-mail de conclusão.

## **3.2 Fase 1 --- Login e navegação (SIMBOLUS)**

  -----------------------------------------------------------------------------
  **Passo**   **Ação**              **Resultado**
  ----------- --------------------- -------------------------------------------
  1           Abre o SIMBOLUS       Sistema iniciado via app.bat

  2           Login                 Autenticado com Empresa 1, Usuário TI
                                    CORTEL, Senha 514020

  3           Navega até Contas a   Tela Contas a Receber aberta e posicionada
              Receber               com filtros em branco

  4           Chama o próximo robô  SIMBOLUS_NFSe_GERA_LOTES iniciado
  -----------------------------------------------------------------------------

## **3.3 Fase 1 --- Geração por tipo de conta (SIMBOLUS_NFSe_GERA_LOTES)**

A tela utilizada é Contas a Receber do SIMBOLUS. Os campos configurados
pelo robô em cada grupo são: Conta (dropdown), Filtrar por Período,
Status, Período De/Até e Notas Fiscais. Após configurar os filtros e
clicar em Exibir, o robô aciona o botão NFS-e na barra de ações, aguarda
o popup de confirmação e faz OCR para extrair os números de RPS.

Variáveis inicializadas: array = \[\] (acumula todos os RPS),
range_final = data corrente (DDMMAAAA), range_inicio = mês/ano corrente
(MMAAAA), primeiro_dia = \'01\'.

  --------------------------------------------------------------------------------------------------------
  **Grupo**      **Conta**      **Filtrar    **Status**      **Notas     **Arquivo OCR gerado** **Tempo de
                                por                          Fiscais**                          espera**
                                Período**                                                       
  -------------- -------------- ------------ --------------- ----------- ---------------------- ----------
  1 ---          MANUTENÇÃO     Pagamento    Pagos           SEM NF      SIMBOLUS_MANUT.png     100s
  MANUTENÇÃO                                                 EMITIDA                            

  2 ---          VENDA DE       Pagamento    Pagos           SEM NF      SIMBOLUS_SEPULT.png    40s
  SEPULTAMENTO   SERVIÇOS -                                  EMITIDA                            
                 SEPULTAMENTO                                                                   

  3 --- LÁPIDE   VENDA DE       Pagamento    Pagos           SEM NF      SIMBOLUS_LAPIDE.png    30s
                 SERVIÇOS -                                  EMITIDA                            
                 LAPIDES                                                                        

  4 --- JAZIGOS  VENDA DE       Vencimento   Abertos/Todos   SEM NF      SIMBOLUS_JAZIGOS.png   180s
                 JAZIGOS                                     EMITIDA                            
  --------------------------------------------------------------------------------------------------------

Para cada grupo, o fluxo é:

-   Configura os filtros na tela Contas a Receber conforme a tabela
    acima.

-   Clica em Exibir e aguarda o carregamento dos resultados.

-   Aciona o botão NFS-e na barra de ações.

-   Popup \'Lote RPS Gerado com sucesso\' exibe os números dos RPS
    gerados.

-   Faz screenshot do popup e envia para OCR (api.ocr.space) --- arquivo
    salvo em C:\\CorteX\\SIMBOLUS\\.

-   Extrai os números de RPS do retorno OCR e acumula no array.

-   Fecha o popup e retorna aos filtros para o próximo grupo.

## **3.4 Fase 1 --- Finalização e chamada da Fase 2**

-   Após os 4 grupos: envia e-mail de backup com o array completo para
    rafael.dunker@cortel.com.br, lucas.alves@cortel.com.br --- assunto:
    bkp_array\_{range_final}.

-   Chama SIMBOLUS_ENVIO_NFSE.

## **3.5 Fase 2 --- Login e navegação (SIMBOLUS_ENVIO_NFSE)**

  -----------------------------------------------------------------------------
  **Passo**   **Ação**               **Resultado**
  ----------- ---------------------- ------------------------------------------
  1           Inicializa variáveis e array_lote_erro = \[\], count_erro = 0.
              configura e-mail       Outlook365 configurado com
                                     cortex@cortel.com.br

  2           Abre o SIMBOLUS em     Sistema iniciado via app_nfse.bat
              modo NFS-e             

  3           Login                  Autenticado com Empresa 1, Usuário TI
                                     CORTEL, Senha 514020

  4           Navega até a tela      Tela \'Nota Fiscal de Serviço Eletrônica
              NFS-e                  (NFS-e)\' aberta
  -----------------------------------------------------------------------------

## 

## **3.6 Fase 2 --- Loop de envio por RPS**

Para cada número de RPS no array:

  ----------------------------------------------------------------------------
  **Sub-etapa**   **O que acontece**           **Resultado**
  --------------- ---------------------------- -------------------------------
  a\) Localização O robô acessa o campo de     Lote localizado na tela
                  busca da tela NFS-e e        
                  informa o número do lote     
                  (RPS)                        

  b\) Busca na    O robô percorre a grid       Lote com data preenchida e
  lista           alterando as datas das 10    pronto para transmissão
                  notas que são permitidas por 
                  lote                         

  c\) Transmissão O robô confirma e transmite  Lote enviado --- aguarda
                  o lote para a prefeitura     retorno da prefeitura (até 90s)

  d\) Verificação O robô verifica o resultado  Se sucesso: avança para o
                  da transmissão na tela ---   próximo RPS. Se erro: aplica o
                  sucesso ou erro              tratamento da seção 3.7
  ----------------------------------------------------------------------------

## **3.7 Fase 2 --- Tratamento de erros**

  -----------------------------------------------------------------------------------
  **Condição**          **O que o robô faz**
  --------------------- -------------------------------------------------------------
  Erro IBGE detectado   Envia e-mail para contasareceber@cortel.com.br (cc:
  na tela               rafael.dunker) --- assunto: SIMBOLUS_erro_IBGE_lote\_{rps}.
                        Fecha a tela de erro e avança para o próximo RPS.

  Lote não transmitido  Adiciona o RPS ao array_lote_erro. Captura screenshot da aba
  (retorno de erro da   Log (salvo em C:\\CorteX\\SIMBOLUS\\LOTE_COM_ERRO.png). Envia
  prefeitura)           e-mail para contasareceber@cortel.com.br (cc: rafael.dunker,
                        lucas.alves) com a imagem anexa --- assunto:
                        LOTE_NAO_TRANSMITIDO\_{rps}. Incrementa count_erro. Avança
                        para o próximo RPS.

  5 erros consecutivos  Interrompe a execução. Envia e-mail com assunto
  (count_erro \>= 5)    SIMBOLUS_INTERROMPIDO_POR_ERROS_CONSECUTIVOS\_{range_final} e
                        lista dos lotes em array_lote_erro. Reseta count_erro = 0.
  -----------------------------------------------------------------------------------

## **3.8 Fase 2 --- Finalização**

-   Envia e-mail para contasareceber@cortel.com.br com a lista completa
    de lotes não transmitidos (array_lote_erro) --- assunto:
    SIMBOLUS_verificar_lotes_não_transmitidos\_{range_final}.

-   Fecha a tela NFS-e do SIMBOLUS.

-   Envia e-mail de conclusão --- assunto:
    SIMBOLUS_NFSe\_{range_final}\_CONCLUÍDO --- corpo: \'Envio de notas
    de manutenção, lápides, sepultamento e jazigos concluído, favor
    verificar.\'

# 

# 

# 

# **4. Log e notificação**

  -------------------------------------------------------------------------------------------------------------------------------------------
  **Momento**    **Destinatário(s)**            **CC**           **Assunto**                                            **Conteúdo**
  -------------- ------------------------------ ---------------- ------------------------------------------------------ ---------------------
  Após Fase 1    rafael.dunker, lucas.alves     ---              bkp_array\_{data}                                      Array com todos os
                 \@cortel.com.br                                                                                        RPS gerados

  Erro IBGE      contasareceber@cortel.com.br   rafael.dunker    SIMBOLUS_erro_IBGE_lote\_{rps}                         Notificação
                                                                                                                        automática

  Lote não       contasareceber@cortel.com.br   rafael.dunker,   LOTE_NAO_TRANSMITIDO\_{rps}                            Screenshot da aba Log
  transmitido                                   lucas.alves                                                             (LOTE_COM_ERRO.png)
                                                                                                                        como anexo

  5 erros        contasareceber@cortel.com.br   rafael.dunker,   SIMBOLUS_INTERROMPIDO_POR_ERROS_CONSECUTIVOS\_{data}   Execução
  consecutivos                                  lucas.alves                                                             interrompida + lista
                                                                                                                        do array_lote_erro

  Lista de       contasareceber@cortel.com.br   rafael.dunker,   SIMBOLUS_verificar_lotes_não_transmitidos\_{data}      Lista completa do
  falhas                                                                                                                array_lote_erro

  Conclusão      contasareceber@cortel.com.br   rafael.dunker,   SIMBOLUS_NFSe\_{data}\_CONCLUÍDO                       Envio concluído,
                                                lucas.alves                                                             favor verificar
  -------------------------------------------------------------------------------------------------------------------------------------------

# **5. Variáveis do processo**

  -----------------------------------------------------------------------------
  **Variável**      **Tipo**   **Descrição**
  ----------------- ---------- ------------------------------------------------
  array             lista      Acumula todos os números de RPS gerados na Fase
                               1; consumido na Fase 2

  array_lote_erro   lista      Acumula os RPS que falharam na transmissão

  range_final       string     Data corrente em DDMMAAAA

  range_inicio      string     Mês/ano corrente em MMAAAA

  primeiro_dia      string     Fixo \'01\'

  senha             password   Senha do usuário TI CORTEL no SIMBOLUS

  rps               string     Número do RPS corrente no loop da Fase 2

  contador          inteiro    Posição na grid de busca (0 a 9) no loop da Fase
                               2

  count_erro        inteiro    Contador de erros consecutivos na Fase 2 ---
                               para a execução ao atingir 5

  lote_ok           boolean    Flag de lote com erro de transmissão (detectado
                               via reconhecimento de tela)

  ibge              boolean    Flag de erro IBGE (detectado via reconhecimento
                               de tela)

  if_wait           boolean    Flag de controle de fluxo na Fase 1 --- indica
                               se a tela retornou resultados após Exibir

  ocr               lista      Resultado bruto do OCR --- parseado por script
                               Python para extrair os números de RPS
  -----------------------------------------------------------------------------

# **6. Caminhos e arquivos**

  -----------------------------------------------------------------------------------------------
  **Caminho**                                                      **Descrição**
  ---------------------------------------------------------------- ------------------------------
  \\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\app.bat        Abre o SIMBOLUS para a Fase 1
                                                                   (geração de lotes)

  \\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\app_nfse.bat   Abre o SIMBOLUS para a Fase 2
                                                                   (envio de NFS-e)

  C:\\CorteX\\CORTEL_RS\\SIMBOLUS_NFSE.db                          Banco Rocketbot com os 6 robôs
                                                                   do projeto

  C:\\CorteX\\SIMBOLUS\\SIMBOLUS_MANUT.png                         Screenshot do popup \'Lote RPS
                                                                   Gerado com sucesso\' ---
                                                                   Manutenção (sobrescrito a cada
                                                                   execução)

  C:\\CorteX\\SIMBOLUS\\SIMBOLUS_SEPULT.png                        Screenshot do popup ---
                                                                   Sepultamento (sobrescrito a
                                                                   cada execução)

  C:\\CorteX\\SIMBOLUS\\SIMBOLUS_LAPIDE.png                        Screenshot do popup --- Lápide
                                                                   (sobrescrito a cada execução)

  C:\\CorteX\\SIMBOLUS\\SIMBOLUS_JAZIGOS.png                       Screenshot do popup ---
                                                                   Jazigos (sobrescrito a cada
                                                                   execução)

  C:\\CorteX\\SIMBOLUS\\LOTE_COM_ERRO.png                          Screenshot da aba Log quando
                                                                   um lote falha na transmissão
                                                                   (sobrescrito a cada erro)
  -----------------------------------------------------------------------------------------------

# **7. Riscos e premissas**

## **7.1 Riscos identificados**

  -----------------------------------------------------------------------
  **Risco**                  **Impacto**
  -------------------------- --------------------------------------------
  Mudança de layout, posição Robô para sem aviso --- toda a automação
  de campos ou texto de      depende da interface gráfica
  popups no SIMBOLUS         

  api.ocr.space indisponível Array fica vazio ou com dados incorretos ---
  ou retorno incorreto       Fase 2 não transmite nada

  Ordem das contas no        Robô selecionará a conta errada
  dropdown Conta for         silenciosamente
  alterada no SIMBOLUS       

  RPS gerado na posição além Lote não será localizado e irá para
  da 10ª linha da grid (Fase array_lote_erro sem tentativa de envio
  2)                         

  Sessão RDP bloqueada ou    Robô não inicia --- automação exige sessão
  servidor reiniciado no     interativa ativa
  horário de execução        

  Instabilidade do servidor  Execução pode ser interrompida sem
  10.1.253.55                notificação
  -----------------------------------------------------------------------

## **7.2 Premissas**

-   Sessão RDP 10.1.253.55 está ativa e desbloqueada no horário de
    execução.

-   O SIMBOLUS está acessível via rede e o login TI CORTEL / 514020 está
    válido.

-   A api.ocr.space está operacional e a chave K89012960388957 é válida.

-   O Outlook365 está configurado no Rocketbot com a conta
    cortex@cortel.com.br.

-   Os arquivos app.bat e app_nfse.bat estão presentes no caminho de
    rede.

*--- Fim do documento ---*
