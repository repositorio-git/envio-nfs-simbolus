**RPA NFS-e SIMBOLUS**

Documento Técnico de Requisitos

*Geração e Envio Automatizado de NFS-e no SIMBOLUS --- Memorial Parque
Jardim dos Girassóis*

  ---------------------- ------------------------------------------------
  **Empresa**            Cortel

  **Produto / Sistema**  RPA --- Geração e Envio Automatizado de NFS-e no
                         SIMBOLUS (Python REFramework)

  **Versão**             1.0

  **Data**               01/08/2026

  **Status**             Rascunho

  **Responsável**        Equipe de RPA / TI Cortel

  **Documento de         Especificação de Negócio RPA NFS-e SIMBOLUS v3
  origem**               (Dunker --- funcional, Lucas --- implementação
                         RPA)
  ---------------------- ------------------------------------------------

**Sumário**

1\. Introdução

2\. Requisitos Funcionais

3\. Telas e Interfaces do SIMBOLUS Envolvidas

4\. Requisitos Não Funcionais

5\. Integrações

6\. Modelo de Dados

7\. Restrições e Premissas

8\. Histórico do Documento

9\. Análise Técnica e Recomendações de Otimização

**1. Introdução**

**1.1. Objetivo**

Migrar, de Rocketbot para Python REFramework, o processo diário de
geração e envio de Notas Fiscais de Serviço Eletrônicas (NFS-e) no
sistema SIMBOLUS, operado pelo Memorial Parque Jardim dos Girassóis. O
robô automatiza a execução que hoje ocorre às 16h: geração de lotes de
RPS para os 4 tipos de conta (Manutenção, Sepultamento, Lápide e
Jazigos) e transmissão de cada lote para a prefeitura. A migração
introduz controle de estado persistente via tabelas NFSE_LOTE e
NFSE_RPS, eliminando a perda de progresso em caso de interrupção e
viabilizando a validação assíncrona de lotes sem resposta da prefeitura.

**1.2. Escopo do Projeto**

**Dentro do escopo:**

-   Automação da geração de lotes RPS para os 4 tipos de conta do
    Memorial Parque Jardim dos Girassóis: Manutenção, Sepultamento,
    Lápide e Jazigos.

-   Transmissão de cada lote RPS gerado para a prefeitura via tela
    \"Nota Fiscal de Serviço Eletrônica\" do SIMBOLUS.

-   Extração dos números de RPS do popup \"Lote RPS Gerado com sucesso\"
    via OCR (OCR.space API).

-   Controle de estado persistente via tabelas NFSE_LOTE e NFSE_RPS:
    checkpoint de retomada por fase em caso de interrupção.

-   Validação assíncrona de lotes transmitidos sem confirmação de
    retorno da prefeitura.

-   Tratamento automatizado dos erros conhecidos: erro IBGE, lote não
    transmitido e 5 erros consecutivos.

-   Notificações por e-mail em todos os eventos relevantes (backup do
    array, erros, conclusão).

-   Execução via Windows Task Scheduler (RPA_SIMBOLUS_MANUT), diária às
    16:00, servidor 10.1.253.55.

**Fora do escopo (esta versão):**

-   SIMBOLUS_ENVIO_ASSISTIDO_MANUT --- envio assistido de manutenção
    (robô separado, fora deste fluxo).

-   SIMBOLUS_AJUSTA_DATAS --- ajuste manual de datas em RPS existentes.

-   SIMBOLUS_REENVIO_LOTES --- reenvio manual de lotes com erro.

-   Tratamento ou correção dos erros retornados pela prefeitura ---
    responsabilidade da área financeira.

-   Geração de NFS-e de datas diferentes da data de execução.

**1.3. Público-Alvo do Sistema**

  -----------------------------------------------------------------------
  **Perfil**               **Descrição**
  ------------------------ ----------------------------------------------
  Robô Python REFramework  Executa o fluxo completo sem intervenção
  (execução automatizada)  humana, no servidor 10.1.253.55, usuário
                           MATRIZ\\CORTEX, sessão RDP interativa

  Área Financeira ---      Recebe todos os e-mails de notificação: backup
  Contas a Receber         do array, erros de lote, conclusão; trata
                           manualmente lotes em erro

  Responsável Funcional    Homologa o robô por tipo de conta, valida
  (Dunker)                 filtros do SIMBOLUS e regras de OCR

  TI / Implementação RPA   Desenvolve, mantém e monitora o robô; recebe
  (Lucas)                  cópia nos e-mails de falha grave
  -----------------------------------------------------------------------

**1.4. Convenções e Rastreabilidade**

-   RF-XX --- Requisito Funcional.

-   RNF-XX --- Requisito Não Funcional.

-   INT-XX --- Requisito de Integração.

A coluna Vínculos indica os demais requisitos diretamente relacionados.

**1.5. Contexto e Motivação**

O processo de geração e envio de NFS-e no SIMBOLUS é executado hoje
manualmente ou via Rocketbot --- plataforma em processo de
descontinuação na Cortel. A implementação atual não possui controle de
estado persistente: se o robô for interrompido no meio do processo, não
há como saber quais lotes já foram gerados, quais foram transmitidos e
quais estão pendentes, exigindo reinício completo com risco de
duplicação. Adicionalmente, a transmissão é assíncrona: o SIMBOLUS envia
o lote e aguarda a resposta da prefeitura, que pode não chegar dentro do
timeout da execução. Sem controle de estado, esses lotes \"em aberto\"
se perdem. O objetivo é migrar para Python REFramework com controle de
estado robusto, eliminando dependência do Rocketbot e padronizando o
padrão de desenvolvimento de RPA da equipe Cortel.

**1.6. Princípios de Arquitetura**

**Nota arquitetural:** O robô é um único processo Python (tarefas.py)
com dois blocos sequenciais: Fase 1 --- Geração e Fase 2 ---
Transmissão. A automação ocorre por \*\*tela\*\* (PyAutoGUI + win32gui
para interagir com o SIMBOLUS) e por \*\*banco de dados\*\* (acesso
direto ao Firebird do Simbolus via driver fdb para controle de estado).
A extração dos números de RPS do popup é feita via OCR.space. O controle
de lotes e notas enviadas reside nas tabelas NFSE_LOTE e NFSE_RPS no
próprio Firebird do Simbolus --- o robô consulta e atualiza esses
registros ao longo de todo o processo.

-   Interação por tela: ações no SIMBOLUS (navegar, clicar, preencher
    campos, detectar popups) ocorrem via PyAutoGUI (coordenadas e
    imagens) e win32gui (foco de janela). Mudanças de layout ou posição
    de botões no SIMBOLUS podem quebrar o robô sem aviso prévio.

-   Interação por banco de dados: leitura de registros elegíveis,
    contagem para cálculo de timeout (RF-14a), e controle de estado das
    tabelas NFSE_LOTE e NFSE_RPS ocorrem via acesso direto ao Firebird
    do Simbolus (driver fdb). Ambas as formas de interação --- tela e
    banco --- coexistem e se complementam ao longo do processo.

-   Classificação de erros obrigatória: todo erro é classificado em
    ExcecaoNegocio (erro de negócio esperado --- log e segue) ou
    ExcecaoSistema (falha técnica --- retry antes de encaminhar para
    revisão humana). Nunca se usa Exception genérica. A classe
    excecoes.py é o contrato entre paginas/, dados/ e processo.py.

-   Controle de estado persistente: NFSE_LOTE e NFSE_RPS registram o
    estado de cada lote e nota em todas as fases, permitindo retomada
    exata em caso de interrupção sem reprocessar o que já foi concluído.

-   Checkpoint por fase: o pré-passo da próxima execução detecta onde o
    processo parou e retoma a partir daí.

-   Sessão RDP obrigatória: PyAutoGUI exige sessão Windows interativa
    ativa com tela desbloqueada no servidor 10.1.253.55.

-   OCR como ponto crítico: a extração dos RPS depende da API OCR.space.
    Falha de OCR deve ser tratada como erro de negócio --- o robô não
    pode inferir os RPS sem lê-los do popup.

-   Falha segura por tipo de conta e por lote: falha em um tipo de conta
    não bloqueia os demais; falha em um lote não interrompe os demais,
    exceto no caso de 5 erros consecutivos.

-   Auditabilidade: cada execução gera log estruturado (planilha) por
    execução e e-mails de notificação, permitindo reconstrução histórica
    de qualquer dia de operação.

**2. Requisitos Funcionais**

**2.1. Orquestração e Inicialização do Robô**

  ---------------------------------------------------------------------------------
  **ID**       **Descrição do Requisito**                            **Vínculos**
  ------------ ----------------------------------------------------- --------------
  **RF-01**    O robô deve ser um único processo Python              RF-02
               (**tarefas.py**), disparado pela tarefa               
               **RPA_SIMBOLUS_MANUT** do Windows Task Scheduler às   
               **16:00**, todos os dias úteis, no servidor           
               **10.1.253.55**, usuário **MATRIZ\\CORTEX**. A tarefa 
               deve invocar executar_robo.bat, que ativa o ambiente  
               virtual e chama tarefas.py. Não deve haver tarefas    
               separadas por tipo de conta.                          

  **RF-01a**   O projeto deve conter o arquivo **excecoes.py** com   RF-02b, RNF-05
               duas classes de exceção que classificam toda falha do 
               robô: **ExcecaoNegocio** --- erro esperado de         
               negócio, o item é registrado e o robô segue para o    
               próximo lote (sem retry); **ExcecaoSistema** ---      
               falha técnica inesperada, o item passa por retry      
               antes de ser encaminhado para revisão humana. Todo    
               \`raise\` dentro de \`paginas/\` e \`dados/\` deve    
               usar uma dessas duas classes --- nunca \`Exception\`  
               genérica. Mapeamento para este robô: ExcecaoNegocio   
               cobre erro IBGE (RF-26), lote não transmitido pela    
               prefeitura (RF-27) e OCR sem RPS identificáveis       
               (RF-17); ExcecaoSistema cobre SIMBOLUS que não abre,  
               janela não encontrada por PyAutoGUI, queda de conexão 
               com o Firebird e timeout da API OCR.space.            

  **RF-02**    O bloco de inicialização (**inicializar()**) deve:    RF-01, RF-03
               (a) verificar o arquivo PARAR.flag e abortar se       
               encontrado; (b) abrir conexão com o **Firebird do     
               Simbolus** via dados/conexao.py (driver fdb); (c)     
               carregar as configurações dos 4 tipos de conta a      
               partir de configuracoes.py; (d) registrar início da   
               execução e atualizar saida/pulso.json.                

  **RF-02a**   O método **obter_item()** deve consultar a tabela     RF-02, RF-21,
               NFSE_LOTE no Firebird buscando o próximo registro com RF-22
               status **GERADO**, ordenado por data_geracao (mais    
               antigo primeiro). Deve retornar o registro completo   
               do lote (numero_rps, tipo_conta, id_lote) ou **None** 
               quando a fila estiver vazia --- sinalando ao loop     
               principal em \`processo.py\` que a Fase 2 encerrou. O 
               método nunca deve alterar o status do lote: a         
               transição para EM_TRANSMISSAO é responsabilidade de   
               \`processar_item()\` (RF-22).                         

  **RF-02b**   O método **processar_item(lote)** deve encapsular     RF-01a, RF-22,
               toda a lógica de transmissão de um único lote,        RF-25, RF-26,
               incluindo o loop de retry para **ExcecaoSistema**.    RF-27, RNF-10
               Para cada lote: tenta transmitir até                  
               **max_tentativas_por_item** vezes (configurável em    
               configuracoes.py, padrão 2); se todas as tentativas   
               resultarem em ExcecaoSistema, registra o lote como    
               **ERRO_TRANSMISSAO** e o adiciona ao array_lote_erro  
               para revisão humana; se ocorrer **ExcecaoNegocio**    
               (IBGE, rejeição de prefeitura), registra o status     
               específico e segue sem retry. O parâmetro             
               max_tentativas_por_item nunca deve ser hardcoded.     

  **RF-03**    O robô deve expor o parâmetro **ate_etapa** via       RF-02
               sys.argv, aceitando os valores: inicializar,          
               gerar_lotes, transmitir_lotes, validar_lotes. Permite 
               execução parcial de cada fase de forma isolada para   
               debug ou retomada manual.                             

  **RF-04**    O robô deve verificar o kill switch (**PARAR.flag**)  RF-02, RNF-04
               ao início de cada ciclo por tipo de conta (Fase 1) e  
               ao início de cada lote (Fase 2), interrompendo a      
               execução de forma segura sem abortar operações de     
               banco em andamento.                                   

  **RF-05**    O robô deve executar sequencialmente: (1) Pré-passo   RF-02, RF-35
               de retomada → (2) Fase 1 --- Geração → (3) Fase 2 --- 
               Transmissão → (4) Validação assíncrona → (5) Log e    
               encerramento. O **finalizar()** deve executar sempre, 
               mesmo após erro fatal, dentro de finally.             
  ---------------------------------------------------------------------------------

**2.2. Pré-passo de Verificação e Retomada de Lotes Pendentes**

  --------------------------------------------------------------------------------
  **ID**      **Descrição do Requisito**                            **Vínculos**
  ----------- ----------------------------------------------------- --------------
  **RF-06**   Ao iniciar, o robô deve consultar a tabela NFSE_LOTE  RF-07, RF-08
              buscando lotes nos status **GERADO** (gerado via OCR, 
              não transmitido) ou **TRANSMITIDO_SEM_CONFIRMACAO**   
              (transmitido, sem retorno da prefeitura dentro do     
              timeout), independentemente da data. Lotes em aberto  
              de execuções anteriores devem ser priorizados antes   
              de gerar novos lotes do dia.                          

  **RF-07**   Para cada lote em status **GERADO** encontrado no     RF-06, RF-20
              pré-passo, o robô deve retomar a transmissão (Fase 2) 
              antes de executar a geração de novos lotes do dia. O  
              número RPS já consta na tabela NFSE_LOTE --- não é    
              necessário reabrir o SIMBOLUS em modo de geração.     

  **RF-08**   Para cada lote em status                              RF-06, RF-31
              **TRANSMITIDO_SEM_CONFIRMACAO**, o robô deve tentar   
              validar o resultado: (a) via consulta ao Firebird do  
              Simbolus, se FIREBIRD_HOST estiver configurado no     
              .env; (b) via reabertura da tela NFS-e do SIMBOLUS    
              para verificação visual. Se ainda sem resposta, deve  
              incrementar tentativas_validacao e manter o status.   

  **RF-09**   O robô deve registrar no log da execução a quantidade RF-06, RF-35
              de lotes retomados por status                         
              (**qt_lotes_retomados_gerado**,                       
              **qt_lotes_retomados_sem_confirmacao**) e o resultado 
              de cada retomada.                                     
  --------------------------------------------------------------------------------

**2.3. Fase 1 --- Geração de Lotes por Tipo de Conta**

  ------------------------------------------------------------------------------------------
  **ID**       **Descrição do Requisito**                                     **Vínculos**
  ------------ -------------------------------------------------------------- --------------
  **RF-10**    O robô deve abrir o SIMBOLUS via **app.bat**                   RF-11
               (\\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\app.bat),   
               aguardar a tela de login e autenticar com **Empresa 1**,       
               usuário **TI CORTEL** e senha armazenada no .env. O caminho do 
               app.bat deve ser configurável em configuracoes.py.             

  **RF-11**    Após o login, o robô deve navegar até a tela **Contas a        RF-10, RF-12
               Receber** do SIMBOLUS e aguardar o carregamento completo com   
               todos os campos de filtro em branco antes de prosseguir.       

  **RF-12**    O robô deve percorrer sequencialmente os 4 grupos de tipo de   RF-11, RF-13
               conta na ordem configurada em configuracoes.py, aplicando os   
               filtros correspondentes na tela Contas a Receber conforme      
               tabela abaixo. Os parâmetros de filtro (Conta, Filtrar por     
               Período, Status, Notas Fiscais, tempo de espera) devem ser     
               integralmente configuráveis.                                   

  **RF-13**    Após aplicar os filtros, o robô deve clicar em **Exibir** e    RF-12, RF-14
               aguardar o carregamento. Se a tela retornar sem resultados     
               (flag if_wait false), deve registrar no log que não havia      
               contas elegíveis para aquele tipo e avançar para o próximo     
               grupo sem gerar erro.                                          

  **RF-14**    Para cada grupo com resultados, o robô deve acionar o botão    RF-13, RF-14a,
               **NFS-e** na barra de ações do SIMBOLUS e monitorar a tela em  RF-15, RF-16
               polling de \~5 segundos aguardando o popup **\"Lote RPS Gerado 
               com sucesso\"**. A detecção é por estado da tela --- o robô    
               não dorme por tempo fixo; avança assim que o popup for         
               identificado. O timeout máximo de espera deve ser calculado    
               dinamicamente com base na quantidade de registros elegíveis    
               consultada no Firebird antes do clique (ver RF-14a).           

  **RF-14a**   Antes de clicar no botão NFS-e, o robô deve consultar no       RF-14, RF-15
               **Firebird do Simbolus** a quantidade de registros elegíveis   
               para o tipo de conta corrente (mesmos critérios dos filtros    
               aplicados na tela). O timeout máximo de espera pelo popup deve 
               ser proporcional a essa contagem: timeout_max =                
               base_por_registro × qt_registros, com valor mínimo e máximo    
               configuráveis em configuracoes.py. Isso garante que grupos com 
               poucos registros não aguardem desnecessariamente e grupos      
               grandes recebam tempo suficiente.                              

  **RF-15**    Ao detectar o popup \"Lote RPS Gerado com sucesso\", o robô    RF-14, RF-16,
               deve: (a) capturar screenshot do popup (salvo em               INT-02
               C:\\CorteX\\SIMBOLUS\\SIMBOLUS\_{TIPO}.png, sobrescrito a cada 
               execução); (b) enviar a imagem para a **API OCR.space** com    
               chave configurada no .env; (c) aguardar o retorno da API.      

  **RF-16**    O robô deve processar o retorno da API OCR.space via módulo    RF-15, RF-17,
               isolado em dados/, parseando o texto para extrair os **números RF-18
               de RPS**. Cada número extraído deve gerar um registro em       
               **NFSE_LOTE** com status GERADO, vinculado ao tipo de conta e  
               à data de execução.                                            

  **RF-17**    Se a API OCR.space retornar erro, timeout ou retorno sem RPS   RF-16, RF-35,
               identificáveis, o robô deve: registrar no log; marcar o tipo   RNF-06
               de conta como **ERRO_OCR** no log; não gerar registro em       
               NFSE_LOTE; enviar e-mail de alerta para a TI; e avançar para o 
               próximo grupo sem interromper a execução.                      

  **RF-18**    Após os 4 grupos da Fase 1, o robô deve enviar **e-mail de     RF-16, INT-03
               backup** para rafael.dunker@cortel.com.br e                    
               lucas.alves@cortel.com.br, assunto **bkp_array\_{DDMMAAAA}**,  
               com a lista completa de todos os RPS gerados (extraída da      
               tabela NFSE_LOTE com status GERADO da data corrente).          

  **RF-19**    Ao fechar cada popup após o OCR, o robô deve usar taskkill ou  RF-14, RF-15
               win32gui para garantir que o popup foi fechado antes de        
               configurar os filtros do próximo grupo, evitando interferência 
               de janelas residuais.                                          
  ------------------------------------------------------------------------------------------

**Tabela de filtros por tipo de conta --- parametrizada em
configuracoes.py. O timeout de espera pelo popup é calculado
dinamicamente via Firebird (RF-14a) --- não há valores fixos por tipo de
conta:**

  ----------------------------------------------------------------------------------------
  **Grupo**      **Conta             **Filtrar    **Status**      **Notas      **Timeout
                 (dropdown)**        por                          Fiscais**    popup**
                                     Período**                                 
  -------------- ------------------- ------------ --------------- ------------ -----------
  1 ---          MANUTENÇÃO          Pagamento    Pagos           SEM NF       Dinâmico
  MANUTENÇÃO                                                      EMITIDA      ---
                                                                               Firebird

  2 ---          VENDA DE SERVIÇOS - Pagamento    Pagos           SEM NF       Dinâmico
  SEPULTAMENTO   SEPULTAMENTO                                     EMITIDA      ---
                                                                               Firebird

  3 --- LÁPIDE   VENDA DE SERVIÇOS - Pagamento    Pagos           SEM NF       Dinâmico
                 LAPIDES                                          EMITIDA      ---
                                                                               Firebird

  4 --- JAZIGOS  VENDA DE JAZIGOS    Vencimento   Abertos/Todos   SEM NF       Dinâmico
                                                                  EMITIDA      ---
                                                                               Firebird
  ----------------------------------------------------------------------------------------

**2.4. Fase 2 --- Transmissão das NFS-e para a Prefeitura**

  ----------------------------------------------------------------------------------------------
  **ID**      **Descrição do Requisito**                                          **Vínculos**
  ----------- ------------------------------------------------------------------- --------------
  **RF-20**   O robô deve abrir o SIMBOLUS em **modo NFS-e** via **app_nfse.bat** RF-21
              (\\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\app_nfse.bat),   
              autenticar com as mesmas credenciais da Fase 1 e navegar até a tela 
              **\"Nota Fiscal de Serviço Eletrônica (NFS-e)\"**.                  

  **RF-21**   Ao iniciar a Fase 2, o robô deve inicializar: array_lote_erro =     RF-20, RF-22
              \[\], count_erro = 0. Deve consultar a tabela NFSE_LOTE buscando    
              todos os registros com status **GERADO** da data corrente           
              (incluindo retomados do pré-passo via RF-07), ordenados por tipo de 
              conta.                                                              

  **RF-22**   Para cada lote em status GERADO: (a) atualizar o status para        RF-21, RF-23
              **EM_TRANSMISSAO** no **Firebird do Simbolus** --- antes de         
              interagir com a UI (checkpoint de fase 2); (b) acessar o campo de   
              busca da tela NFS-e e informar o **número do lote (RPS)** para      
              localizá-lo na grid.                                                

  **RF-23**   Após localizar o lote na grid, o robô deve percorrer as notas do    RF-22, RF-24
              lote (até **10 notas por lote**, posições 0 a 9) preenchendo a      
              **data do dia corrente** em cada linha, via interação direta com os 
              campos da grid usando PyAutoGUI.                                    

  **RF-24**   Após preencher as datas, o robô deve acionar o botão de             RF-23, RF-25,
              **transmissão** do lote e aguardar o retorno do SIMBOLUS/prefeitura RF-26, RF-27
              por até **90 segundos** (configurável). A detecção do resultado é   
              feita por reconhecimento de imagem/texto na tela: sucesso, erro     
              IBGE ou lote não transmitido.                                       

  **RF-25**   Se a transmissão for bem-sucedida: atualizar NFSE_LOTE para         RF-24
              **CONFIRMADO** e registrar data_transmissao; atualizar todos os     
              NFSE_RPS do lote para CONFIRMADO; resetar count_erro = 0; avançar   
              para o próximo lote.                                                

  **RF-26**   Ao detectar **erro IBGE** (via reconhecimento de imagem em          RF-24, RF-35,
              paginas/tela_nfse.py): fechar a tela de erro; atualizar NFSE_LOTE   INT-03
              para **ERRO_IBGE**; enviar e-mail para contasareceber@cortel.com.br 
              (cc: rafael.dunker) com assunto SIMBOLUS_erro_IBGE_lote\_{rps};     
              avançar para o próximo lote sem incrementar count_erro.             

  **RF-27**   Ao detectar **lote não transmitido** (ExcecaoNegocio --- RF-01a):   RF-24, RF-28,
              capturar screenshot da **aba Log** do SIMBOLUS salvo em             RF-35, RF-01a
              **saida/evidencias/lote_erro\_{RPS}\_{DDMMAAAA_HHMM}.png** (nome    
              único por ocorrência --- nunca sobrescreve); atualizar NFSE_LOTE    
              para **ERRO_TRANSMISSAO** no Firebird; adicionar RPS ao             
              array_lote_erro; incrementar count_erro; enviar e-mail para         
              contasareceber@cortel.com.br (cc: rafael.dunker, lucas.alves) com   
              assunto LOTE_NAO_TRANSMITIDO\_{rps} e o screenshot como anexo.      

  **RF-28**   Se count_erro atingir ou superar **5 erros consecutivos**: enviar   RF-27, RF-35
              e-mail de alerta para contasareceber@cortel.com.br (cc:             
              rafael.dunker, lucas.alves, TI) com assunto                         
              **SIMBOLUS_INTERROMPIDO_POR_ERROS_CONSECUTIVOS\_{DDMMAAAA}** e      
              lista do array_lote_erro; resetar count_erro = 0; abortar a Fase 2  
              com status_final_robo = ABORTADO_ERROS_CONSECUTIVOS.                

  **RF-29**   Se a transmissão não retornar resultado dentro do timeout de 90     RF-24, RF-31,
              segundos: atualizar NFSE_LOTE para **TRANSMITIDO_SEM_CONFIRMACAO**  RNF-03
              e registrar data_transmissao; adicionar RPS ao array_lote_erro; não 
              incrementar count_erro; avançar para o próximo lote.                

  **RF-30**   O robô deve aplicar timeout máximo configurável (padrão: 90         RF-05, RNF-01
              minutos) para a Fase 2 completa. Ao exceder, deve abortar com       
              status_final_robo = **ABORTADO_TIMEOUT_FASE2** e prosseguir para    
              encerramento.                                                       
  ----------------------------------------------------------------------------------------------

**2.5. Validação Assíncrona de Lotes Pendentes**

  --------------------------------------------------------------------------------
  **ID**      **Descrição do Requisito**                            **Vínculos**
  ----------- ----------------------------------------------------- --------------
  **RF-31**   Após concluir a Fase 2, o robô deve consultar o       RF-29, RF-32,
              **Firebird do Simbolus** (tabela NFSE_LOTE) buscando  RF-33
              todos os lotes com status                             
              **TRANSMITIDO_SEM_CONFIRMACAO** --- da execução       
              corrente e de execuções anteriores (pré-passo RF-08). 
              Para cada um, deve tentar obter o status final do     
              lote.                                                 

  **RF-32**   A consulta de status deve ser realizada em ordem de   RF-31, RF-33
              prioridade: (a) **via Firebird do Simbolus** --- se   
              FIREBIRD_HOST estiver configurado no .env, executar   
              SELECT nas tabelas do Simbolus; (b) **via UI do       
              SIMBOLUS** --- abrir a tela NFS-e e verificar         
              visualmente o status na grid.                         

  **RF-33**   Se o status for confirmado: atualizar NFSE_LOTE para  RF-32, RF-35
              **CONFIRMADO**, **ERRO_PREFEITURA** ou **PARCIAL**    
              conforme o resultado; atualizar os NFSE_RPS           
              correspondentes. Se ainda sem resposta: incrementar   
              tentativas_validacao; se atingir o limite (padrão:    
              5), atualizar para **PENDENTE_REVISAO_MANUAL** e      
              notificar TI e área financeira.                       

  **RF-34**   O robô deve registrar no log: quantidade de lotes     RF-33, RF-35
              validados, confirmados, com erro de prefeitura, ainda 
              aguardando e movidos para revisão manual.             
  --------------------------------------------------------------------------------

**2.6. Log, Notificação e Encerramento**

  -------------------------------------------------------------------------------------------------------------------------
  **ID**      **Descrição do Requisito**                                                                     **Vínculos**
  ----------- ---------------------------------------------------------------------------------------------- --------------
  **RF-35**   Ao encerrar (**finalizar()** dentro de finally), o robô deve: (a) chamar                       RF-05, RF-02
              **dados.encerrar_conexao()** para fechar a conexão com o Firebird do Simbolus; (b) fechar      
              qualquer janela do SIMBOLUS ainda aberta; (c) gerar/atualizar (append) uma planilha de log em  
              C:\\CorteX\\CORTEL_RS\\ e movê-la via shutil.move para                                         
              \\\\dcsrv01\\Deptos\\Informatica\\ROCKETBOT\\SIMBOLUS_NFSE\\logs\\log_nfse\_{DDMMAAAA}.xlsx. O 
              finalizar() deve executar sempre, mesmo após erro fatal.                                       

  **RF-36**   Ao final da Fase 2, o robô deve enviar e-mail para contasareceber@cortel.com.br (cc:           RF-27, INT-03
              rafael.dunker, lucas.alves) com a lista completa do array_lote_erro --- assunto:               
              **SIMBOLUS_verificar_lotes_não_transmitidos\_{DDMMAAAA}**. O e-mail não deve ser enviado se    
              array_lote_erro estiver vazio.                                                                 

  **RF-37**   Ao final de toda a execução, o robô deve enviar e-mail de conclusão para                       RF-35, INT-03
              contasareceber@cortel.com.br (cc: rafael.dunker, lucas.alves) com assunto                      
              **SIMBOLUS_NFSe\_{DDMMAAAA}\_CONCLUÍDO** e corpo: \"Envio de notas de manutenção, lápides,     
              sepultamento e jazigos concluído, favor verificar.\" com a planilha de log como anexo.         

  **RF-38**   Se status_final_robo iniciar com ABORTADO\_, o e-mail de conclusão deve usar o prefixo         RF-37
              **\[FALHA\]** no assunto, adicionar a TI em cópia e informar o motivo da interrupção.          
  -------------------------------------------------------------------------------------------------------------------------

**3. Telas e Interfaces do SIMBOLUS Envolvidas**

Este projeto não introduz telas novas --- o robô automatiza a interação
com telas já existentes do sistema SIMBOLUS. Esta seção documenta as
interfaces manipuladas em vez de protótipos de tela de um sistema novo.

**3.1. Tela Contas a Receber --- Geração (RF-11 a RF-14)**

**Descrição:** Tela principal da Fase 1. Nela o robô configura os
filtros por tipo de conta e aciona a geração do lote RPS.

**Requisitos cobertos:** RF-11, RF-12, RF-13, RF-14, RF-19

-   Dropdown Conta --- selecionado por tipo de conta (MANUTENÇÃO,
    SEPULTAMENTO, LÁPIDE, JAZIGOS)

-   Filtrar por Período --- Pagamento ou Vencimento

-   Status --- Pagos ou Abertos/Todos

-   Campos De / Até --- preenchidos com primeiro dia do mês e data
    corrente

-   Notas Fiscais --- fixo em \"SEM NF EMITIDA\"

-   Botão Exibir --- carrega os resultados na grid

-   Botão NFS-e na barra de ações --- dispara a geração do lote

**3.2. Popup \"Lote RPS Gerado com sucesso\" (RF-14 a RF-17)**

**Descrição:** Popup exibido após o clique no botão NFS-e, contendo os
números de RPS do lote gerado. É a única fonte dos números de RPS --- o
robô não tem acesso ao banco do SIMBOLUS para consultar esses números. A
extração é feita por screenshot + OCR.space.

**Requisitos cobertos:** RF-14, RF-15, RF-16, RF-17

**Risco crítico:** qualquer alteração no layout, fonte ou posição dos
números de RPS no popup pode resultar em OCR incorreto sem que o robô
detecte o erro.

**3.3. Tela \"Nota Fiscal de Serviço Eletrônica (NFS-e)\" ---
Transmissão (RF-20 a RF-24)**

**Descrição:** Tela principal da Fase 2. Nela o robô localiza cada lote
pelo número de RPS, preenche as datas e aciona a transmissão para a
prefeitura.

**Requisitos cobertos:** RF-20, RF-21, RF-22, RF-23, RF-24

-   Campo de busca por número de lote/RPS

-   Grid com até 10 notas por lote --- campo de data por linha
    (preenchido com a data corrente)

-   Botão de transmissão --- aciona o envio à prefeitura

-   Área de resultado --- detectada por reconhecimento de imagem
    (sucesso, erro IBGE, lote não transmitido)

**3.4. Tela de Erro IBGE (RF-26)**

**Descrição:** Popup exibido quando o lote contém registros com código
IBGE inválido ou ausente. Detectada por reconhecimento de imagem
(PyAutoGUI locateOnScreen). Tratamento incorreto (não fechar ou não
identificar) pode travar o fluxo de transmissão.

**3.5. Aba Log do SIMBOLUS (RF-27)**

**Descrição:** Aba da tela NFS-e que exibe o detalhamento do erro de
transmissão quando um lote é rejeitado pela prefeitura. O robô navega
até esta aba e captura screenshot salvo em
saida/evidencias/lote_erro\_{RPS}\_{DDMMAAAA_HHMM}.png --- nome único
por ocorrência para preservar histórico de todas as falhas. A imagem é
incluída como anexo no e-mail de erro (RF-27).

**4. Requisitos Não Funcionais**

**4.1. Desempenho**

  ---------------------------------------------------------------------------------
  **ID**       **Descrição do Requisito**                            **Vínculos**
  ------------ ----------------------------------------------------- --------------
  **RNF-01**   A Fase 2 (transmissão) deve respeitar o timeout       RF-30
               máximo configurável de 90 minutos no total; ao        
               exceder, a execução é abortada e o encerramento é     
               executado normalmente.                                

  **RNF-02**   A detecção do popup \"Lote RPS Gerado com sucesso\"   RF-14, RF-14a
               deve ser feita por polling do estado da tela          
               (intervalos de \~5 segundos), não por sleep fixo. O   
               timeout máximo é calculado dinamicamente a partir da  
               contagem de registros elegíveis no Firebird (RF-14a): 
               os parâmetros base_por_registro, timeout_minimo e     
               timeout_maximo devem ser configuráveis em             
               configuracoes.py. Nenhum tempo de espera fixo por     
               tipo de conta deve ser hardcoded no código ou na      
               configuração.                                         

  **RNF-03**   O timeout de espera pela resposta da prefeitura       RF-29
               durante a transmissão de cada lote deve ser           
               configurável (padrão: 90 segundos). Ao exceder, o     
               lote é marcado como TRANSMITIDO_SEM_CONFIRMACAO sem   
               incrementar o contador de erros.                      
  ---------------------------------------------------------------------------------

**4.2. Confiabilidade e Disponibilidade**

  ---------------------------------------------------------------------------------
  **ID**       **Descrição do Requisito**                            **Vínculos**
  ------------ ----------------------------------------------------- --------------
  **RNF-04**   O robô deve verificar o kill switch (PARAR.flag) ao   RF-04
               início de cada tipo de conta (Fase 1) e ao início de  
               cada lote (Fase 2). A interrupção deve ser segura --- 
               nunca no meio de uma transação de banco ou de uma     
               operação de UI em andamento.                          

  **RNF-05**   Falha ao processar um tipo de conta na Fase 1 (OCR    RF-17, RF-27
               vazio, timeout de popup) não deve bloquear os tipos   
               seguintes. Falha ao transmitir um lote na Fase 2 não  
               deve bloquear os lotes seguintes, exceto no caso de 5 
               erros consecutivos (RF-28).                           

  **RNF-06**   Se a API OCR.space estiver indisponível ou retornar   RF-17
               erro, o robô deve logar o evento, enviar alerta à TI  
               e avançar para o próximo tipo de conta. Nunca deve    
               tentar inferir os RPS sem o retorno da OCR.           

  **RNF-07**   O finalizar() deve executar sempre (dentro de         RF-05, RF-35
               finally), mesmo que a Fase 1 ou Fase 2 tenham         
               abortado com exceção não tratada --- garantindo que o 
               log e o e-mail de conclusão sejam sempre gerados.     
  ---------------------------------------------------------------------------------

**4.3. Segurança**

  ---------------------------------------------------------------------------------
  **ID**       **Descrição do Requisito**                            **Vínculos**
  ------------ ----------------------------------------------------- --------------
  **RNF-08**   As credenciais do SIMBOLUS (senha TI CORTEL), da API  RF-10, RF-20,
               OCR.space, do Firebird do Simbolus (se configurado) e RF-32
               do Outlook365 devem ser armazenadas exclusivamente no 
               arquivo .env, nunca em configuracoes.py ou no         
               código-fonte. O .env não deve ser versionado.         

  **RNF-09**   O robô deve operar sob o usuário de serviço           RF-01
               MATRIZ\\CORTEX, com acesso restrito ao servidor       
               10.1.253.55 e aos compartilhamentos de rede           
               necessários, sem privilégios adicionais.              

  **RNF-10**   Toda atualização de status nas tabelas de controle    RF-22, RF-25,
               (NFSE_LOTE, NFSE_RPS) deve ser commitada              RF-27
               atomicamente. Nunca deve haver estado parcialmente    
               gravado em caso de exceção durante o commit.          
  ---------------------------------------------------------------------------------

**4.4. Observabilidade**

  ---------------------------------------------------------------------------------
  **ID**       **Descrição do Requisito**                            **Vínculos**
  ------------ ----------------------------------------------------- --------------
  **RNF-11**   Cada execução deve gerar log append-only por execução RF-35
               (planilha), permitindo reconstrução histórica de      
               qualquer dia de operação sem sobrescrever execuções   
               anteriores.                                           

  **RNF-12**   O robô deve manter saida/pulso.json atualizado ao     RF-02
               final de cada fase concluída, contendo: horário do    
               último ciclo, fase atual, quantidade de lotes         
               processados e status. Permite monitoramento externo   
               sem leitura de log.                                   

  **RNF-13**   Toda exceção não tratada deve ser logada com: stack   RF-05, RF-35
               trace completo, fase em execução (Fase 1 ou 2), tipo  
               de conta ou RPS sendo processado e último status      
               registrado no Firebird --- antes de qualquer abort.   
  ---------------------------------------------------------------------------------

**5. Integrações**

  ---------------------------------------------------------------------------------------------------------
  **Sistema / Serviço**                        **Tipo**      **Finalidade**                **Req.
                                                                                           Relacionados**
  -------------------------------------------- ------------- ----------------------------- ----------------
  SIMBOLUS (aplicação desktop)                 UI Automation Sistema alvo da automação --- RF-10 a RF-30
                                               ---           toda interação via interface  
                                               PyAutoGUI +   gráfica; sem API nem          
                                               win32gui      webservice em uso             

  API OCR.space                                REST API      Extração dos números de RPS   RF-15, RF-16,
                                               (HTTPS)       do screenshot do popup \"Lote RF-17
                                                             RPS Gerado com sucesso\"      

  Firebird do Simbolus --- NFSE_LOTE /         Acesso direto Tabelas criadas no próprio    RF-06 a RF-34
  NFSE_RPS                                     via fdb       banco do Simbolus ---         
                                               (Python)      consulta de lotes gerados,    
                                                             controle de notas enviadas e  
                                                             rastreabilidade de cada lote  
                                                             e RPS ao longo do processo    

  Firebird do Simbolus --- tabelas do Simbolus Acesso direto Consulta de números de lote   RF-08, RF-32,
  (leitura)                                    via fdb       gerados pelo Simbolus e       RF-33
                                               (Python)      verificação de status de      
                                                             transmissão --- leitura das   
                                                             tabelas nativas do Simbolus   

  Firebird do Simbolus (opcional)              Acesso direto Validação assíncrona de lotes RF-32, RF-33
                                               via fdb       TRANSMITIDO_SEM_CONFIRMACAO   
                                               (Python)      --- ativo somente se          
                                                             FIREBIRD_HOST estiver no .env 

  SMTP / Outlook365                            E-mail        Backup do array após Fase 1;  RF-18, RF-26 a
                                               (win32com)    alertas de erro IBGE, lote    RF-38
                                                             não transmitido, 5 erros;     
                                                             e-mail de conclusão           

  Compartilhamento de rede                     File share    Armazenamento centralizado da RF-35, RF-10,
  (\\\\dcsrv01\\\...\\SIMBOLUS_NFSE\\logs\\)   (SMB)         planilha de log e dos         RF-20
                                                             arquivos app.bat /            
                                                             app_nfse.bat                  

  Windows Task Scheduler                       Agendador     Disparo único diário às 16:00 RF-01
                                               local         via executar_robo.bat         
  ---------------------------------------------------------------------------------------------------------

**INT-01 --- SIMBOLUS:** integração exclusivamente por automação de
interface; qualquer alteração de menu, posição de botões, texto de
popups ou resolução de tela no servidor 10.1.253.55 pode quebrar o robô
sem aviso prévio. A sessão RDP deve estar ativa e desbloqueada no
horário de execução.

**INT-01 --- SIMBOLUS (UI Automation):** integração exclusivamente por
automação de interface; qualquer alteração de menu, posição de botões,
texto de popups ou resolução de tela no servidor 10.1.253.55 pode
quebrar o robô sem aviso prévio. A sessão RDP deve estar ativa e
desbloqueada.

**INT-02 --- Firebird do Simbolus (fdb):** acesso direto ao banco
Firebird para leitura dos lotes gerados e escrita/atualização de
NFSE_LOTE e NFSE_RPS. As credenciais (host, porta, database, usuário,
senha) devem estar no .env. O schema do Firebird deve ser mapeado antes
da implementação --- alterações de schema pelo fornecedor podem quebrar
as queries sem aviso.

**INT-03 --- OCR.space:** a chave da API deve ser mantida atualizada no
.env. O robô depende criticamente desta API para obter os números de RPS
--- sem OCR, a Fase 2 não tem o que transmitir.

**INT-04 --- Outlook365:** deve estar instalado e configurado com a
conta cortex@cortel.com.br no servidor 10.1.253.55. Módulo win32com
usado para envio de e-mails com anexo.

**6. Modelo de Dados**

**6.1. Entidades de Controle (gerenciadas pelo robô)**

**NFSE_LOTE:** controle de cada lote RPS gerado no SIMBOLUS. Campos:
id_lote (PK), tipo_conta (MANUTENÇÃO / SEPULTAMENTO / LÁPIDE / JAZIGOS),
numero_rps, data_execucao, data_geracao, data_transmissao,
data_confirmacao, status, tentativas_validacao, count_erro_consecutivo,
screenshot_erro_path, observacoes.

**NFSE_RPS:** controle individual de cada nota dentro de um lote.
Campos: id_rps (PK), id_lote (FK → NFSE_LOTE), tipo_conta, numero_rps,
posicao_grid (0 a 9), data_emissao, status, descricao_erro.

**6.2. Diagrama de Status --- NFSE_LOTE**

  ------------------------------------------------------------------------------------------------
  **Status**                    **Descrição**            **RF de     **Transição de Saída**
                                                         Entrada**   
  ----------------------------- ------------------------ ----------- -----------------------------
  GERADO                        RPS extraído via OCR --- RF-16       → EM_TRANSMISSAO
                                não transmitido                      

  EM_TRANSMISSAO                Checkpoint mid-flight:   RF-22       → CONFIRMADO, → ERRO_IBGE, →
                                datas sendo preenchidas              ERRO_TRANSMISSAO, →
                                na UI                                TRANSMITIDO_SEM_CONFIRMACAO

  CONFIRMADO                    Transmissão bem-sucedida RF-25       ---
                                --- estado final de                  
                                sucesso                              

  ERRO_IBGE                     Erro IBGE detectado ---  RF-26       ---
                                área financeira trata                

  ERRO_TRANSMISSAO              Lote rejeitado --- área  RF-27       ---
                                financeira trata                     

  TRANSMITIDO_SEM_CONFIRMACAO   Timeout de resposta ---  RF-29       → CONFIRMADO, →
                                aguarda validação                    ERRO_PREFEITURA, → PARCIAL, →
                                assíncrona                           PENDENTE_REVISAO_MANUAL

  ERRO_OCR                      OCR falhou --- sem       RF-17       ---
                                números de RPS --- TI                
                                verifica                             

  PARCIAL                       Mix de confirmadas e     RF-33       ---
                                erros de prefeitura                  

  ERRO_PREFEITURA               Prefeitura rejeitou      RF-33       ---
                                definitivamente na                   
                                validação assíncrona                 

  PENDENTE_REVISAO_MANUAL       Limite de tentativas de  RF-33       ---
                                validação atingido sem               
                                resposta                             
  ------------------------------------------------------------------------------------------------

**6.3. Entidade de Log Operacional (gerada pelo robô)**

**log_nfse\_{DDMMAAAA}:** data_execucao, fase, tipo_conta,
qt_rps_gerados, qt_lotes_transmitidos, qt_lotes_erro_ibge,
qt_lotes_erro_transmissao, qt_lotes_sem_confirmacao, qt_lotes_validados,
qt_lotes_revisao_manual, array_lote_erro, tempo_execucao_s,
status_final_robo, observacoes.

**7. Restrições e Premissas**

**7.1. Restrições**

-   O robô não trata nem corrige os erros retornados pela prefeitura ---
    responsabilidade da área financeira.

-   O robô não trata os robôs fora do escopo:
    SIMBOLUS_ENVIO_ASSISTIDO_MANUT, SIMBOLUS_AJUSTA_DATAS e
    SIMBOLUS_REENVIO_LOTES.

-   A automação ocorre por tela (UI automation via PyAutoGUI + win32gui)
    e por banco de dados (acesso direto ao Firebird do Simbolus via
    fdb). Não há API REST nem webservice envolvido.

-   Não é permitido gerar ou transmitir NFS-e de datas diferentes da
    data de execução.

-   O robô não detecta erros de OCR com números incorretos (API retorna
    texto errado sem falha explícita) --- apenas erros explícitos de
    retorno da API.

-   A sessão RDP no servidor 10.1.253.55 deve estar ativa e desbloqueada
    no horário de execução.

**7.2. Premissas**

-   A sessão RDP no servidor 10.1.253.55 está ativa, desbloqueada e com
    resolução de tela fixa no horário de execução.

-   O SIMBOLUS está acessível via rede e o login TI CORTEL / senha está
    válido.

-   Os arquivos app.bat e app_nfse.bat estão presentes em
    \\\\dcsrv01\\Deptos\\Informatica\\SIMBOLUS_NOTAS\\.

-   A API OCR.space está operacional e a chave configurada no .env é
    válida.

-   O Outlook365 está instalado e configurado com cortex@cortel.com.br
    no servidor 10.1.253.55.

-   As tabelas NFSE_LOTE e NFSE_RPS serão criadas no Firebird do
    Simbolus antes do início da implementação --- o DDL deve ser
    validado com o time de infraestrutura e compatível com a versão do
    Firebird em uso.

-   A área financeira está ciente de que lotes em ERRO_IBGE,
    ERRO_TRANSMISSAO e PENDENTE_REVISAO_MANUAL seguem para tratamento
    manual.

-   Não há ambiente de homologação representativo --- testes iniciais
    ocorrem em produção com 1 tipo de conta por vez (recomendado: LÁPIDE
    primeiro, por menor tempo de espera e menor volume).

**8. Histórico do Documento**

  ---------------------------------------------------------------------------------
  **Versão**   **Data**     **Autor**           **Descrição**
  ------------ ------------ ------------------- -----------------------------------
  1.0          01/08/2026   Equipe de RPA / TI  Versão inicial do documento técnico
                            Cortel              de requisitos, derivada da
                                                Especificação de Negócio RPA NFS-e
                                                SIMBOLUS v3, incluindo controles de
                                                checkpoint (NFSE_LOTE / NFSE_RPS),
                                                diagrama de estados, validação
                                                assíncrona e análise de migração
                                                Rocketbot → Python REFramework.

  ---------------------------------------------------------------------------------

**9. Análise Técnica e Recomendações de Otimização**

**9.1. Pontos Fortes da Arquitetura Proposta**

-   Controle de estado persistente: a introdução das tabelas NFSE_LOTE e
    NFSE_RPS resolve o principal problema da implementação Rocketbot ---
    a perda de progresso em caso de interrupção. A retomada após
    qualquer falha é feita a partir do pré-passo, sem reprocessar o que
    já foi concluído.

-   Checkpoint EM_TRANSMISSAO gravado antes da UI: a marcação de status
    no banco antes de interagir com o SIMBOLUS é o mecanismo correto
    para detectar interrupções mid-flight. Sem essa marcação, seria
    impossível distinguir \"ainda não processado\" de \"processado mas
    com resultado desconhecido\".

-   Validação assíncrona desacoplada: lotes TRANSMITIDO_SEM_CONFIRMACAO
    são tratados na próxima execução via pré-passo, sem intervenção
    manual e sem bloquear os demais lotes.

-   Fallback UI para validação: a validação assíncrona funciona mesmo
    sem Firebird configurado, via reabertura da tela NFS-e --- robustez
    sem dependência adicional obrigatória.

-   Separação REFramework: a separação processo.py / paginas/ / dados/
    segmenta claramente a lógica de negócio, a interação com o SIMBOLUS
    (paginas/tela_contas_receber.py, paginas/tela_nfse.py) e o acesso a
    dados (dados/banco_controle.py, dados/ocr_service.py).

-   Falha segura por tipo de conta e por lote: falha de OCR em JAZIGOS
    não impede MANUTENÇÃO de transmitir; erro de transmissão em um lote
    não impede os demais.

**9.2. Oportunidades de Otimização**

-   1\. Validação de formato dos RPS pós-OCR: implementar regex ou regra
    de comprimento mínimo para validar os números extraídos antes de
    gravá-los em NFSE_LOTE. Detecta erros de OCR silenciosos (número
    truncado, caractere extra) antes de tentar transmitir.

-   2\. Screenshot de evidências de todas as telas relevantes: incluir
    screenshot das telas de Contas a Receber (após Exibir) e de NFS-e
    (após localizar o lote) no log de evidências (saida/evidencias/),
    independentemente de haver erro. Facilita auditoria e diagnóstico de
    problemas de layout.

-   3\. Monitoramento externo via pulso.json: verificar se pulso.json
    foi atualizado dentro dos últimos 30 minutos após as 16h; se não,
    enviar alerta para a TI --- indica que o robô não iniciou (Task
    Scheduler falhou ou sessão RDP estava bloqueada).

-   4\. Ativação gradual do Firebird do Simbolus: mapear o schema do
    Firebird do Simbolus e ativar a integração opcional (INT-04) para a
    validação assíncrona. Reduz a dependência de abrir a UI do SIMBOLUS
    para checar lotes pendentes.

-   5\. Cache de imagens PyAutoGUI por ambiente: as imagens de
    referência para reconhecimento devem ser capturadas na resolução e
    configuração visual exata do servidor 10.1.253.55 antes do deploy.
    Qualquer mudança de tema Windows, resolução ou DPI invalida as
    imagens de referência.

Nenhuma das recomendações acima é bloqueante para a v1 --- a arquitetura
proposta é operacionalmente sólida e adequada ao contexto (SIMBOLUS via
UI automation, OCR.space disponível, sessão RDP dedicada). As
recomendações visam reduzir a fragilidade de médio prazo e preparar a
solução para evolução futura.

*--- Fim do documento ---*
