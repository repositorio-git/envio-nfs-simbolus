# RPA NFS-e SIMBOLUS — Checklist do que está implementado

Overview funcional do que o robô faz hoje, de ponta a ponta. Onde fizer
sentido, a referência entre parênteses aponta pro requisito correspondente
em `Cortel_RPA-NFSe-SIMBOLUS_Requisitos_v1_0.md`.

## Orquestração geral

- [x] Processo único em Python (`tarefas.py`), que roda as duas fases em
  sequência ou cada uma isolada, por argumento de linha de comando
  (`gerar`, `transmitir`, ou nenhum = as duas) (RF-01).
- [x] Ao iniciar, o robô detecta em que ponto o SIMBOLUS já está (login,
  avisos residuais, menu principal) e só executa o que falta a partir
  dali — não assume que o sistema sempre começa fechado/do zero. Abre o
  SIMBOLUS sozinho (perfil certo pra cada fase) se não encontrar nada
  aberto.
- [x] Encerramento (`finalizar()`) sempre executa ao final, mesmo após
  erro fatal (RF-05, RNF-07).
- [x] Todas as imagens de reconhecimento de tela são carregadas
  automaticamente a partir de uma pasta — basta salvar o `.png`, sem
  cadastro manual em código.

## Fase 1 — Geração de Lotes

- [x] Login automático no SIMBOLUS (RF-10).
- [x] Navega até a tela "Contas a Receber" (RF-11).
- [x] Percorre uma lista configurável de grupos de tipo de conta,
  aplicando os filtros de cada um (conta, período, status, notas
  fiscais) (RF-12).
- [x] Campo "Conta" aceita acentuação (ex.: "VENDA DE SERVIÇOS -
  SEPULTAMENTO") sem perder caracteres, mantendo o filtro de
  autocompletar da tela funcionando normalmente.
- [x] Período "De"/"Até" preenchido automaticamente (primeiro dia do mês
  / data de hoje).
- [x] Se a grid voltar vazia depois de "Exibir", o grupo é pulado sem
  erro e sem travar os demais (RF-13, RNF-05).
- [x] Com resultado, marca tudo e aciona a geração do lote, aguardando a
  confirmação por reconhecimento de tela — sem espera fixa por tempo
  (RF-14, com teto configurável, não calculado dinamicamente pela
  quantidade de registros).

## Fase 2 — Transmissão de Lotes

- [x] Abre o SIMBOLUS no modo NFS-e e navega até a tela de transmissão
  (RF-20).
- [x] Identifica os lotes pendentes de transmissão consultando
  diretamente as tabelas do próprio SIMBOLUS no Firebird.
- [x] Localiza cada lote pelo código (RF-22).
- [x] Corrige a data de emissão das notas cuja competência não é a de
  hoje, antes de transmitir (RF-23).
- [x] Aciona a transmissão e aguarda a conclusão (RF-24), inclusive o
  processamento assíncrono da prefeitura, consultando diretamente o
  Firebird quantas notas do lote ainda não têm número de NFS-e.
- [x] Falha técnica de tela num lote específico é recuperada e o
  processo segue para os próximos lotes, sem travar a fase inteira
  (RNF-05).

## Confiabilidade

- [x] Avisos/popups inesperados (sem significado de negócio) são
  reconhecidos e tratados automaticamente a qualquer momento do fluxo,
  sem precisar de tratamento espalhado pelo código de negócio.
- [x] Erro fatal (travamento de verdade) mata o processo do SIMBOLUS à
  força e tenta a fase inteira de novo do zero (reabre, reloga,
  reconsulta tudo), até um número configurável de vezes antes de
  desistir e devolver o controle pra fora (ex.: próxima execução
  agendada).

## Notificação por e-mail

- [x] Três relatórios por e-mail, cada um no momento certo do fluxo:
  lotes gerados (fim da Fase 1), lotes pendentes de transmissão (início
  da Fase 2) e um relatório pós-processamento (fim da Fase 2), com os
  lotes transmitidos com sucesso e os de envio parcial (transmitidos,
  mas com alguma nota ainda sem número de NFS-e).
- [x] Cada relatório é enviado no máximo uma vez por dia, independente de
  quantas vezes o robô for reiniciado ou reexecutado no mesmo dia.
- [x] Envio via SMTP direto, com a senha vinda só do `.env`.

## Configuração e segredos

- [x] Todas as credenciais (SIMBOLUS, Firebird, e-mail) ficam só no
  `.env`, nunca em `configuracoes.py` nem no código (RNF-08).
- [x] Todo parâmetro operacional (grupos de conta, tempos de espera,
  destinatários de e-mail, tentativas de retentativa) é centralizado em
  `configuracoes.py`.
- [x] Projeto versionado em Git, com `.gitignore` cobrindo segredos
  (`.env`), ambiente virtual e logs.

## Ferramentas de apoio (uso manual, fora do fluxo do robô)

- [x] Script de diagnóstico pra testar o reconhecimento de uma imagem
  específica na tela, com a confiança obtida em cada nível.
- [x] Scripts de diagnóstico de conexão e exploração do schema do
  Firebird do SIMBOLUS.
