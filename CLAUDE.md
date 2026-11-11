# Contexto pra retomar o padrão de trabalho de outro projeto RPA

Este arquivo existe pra fazer uma sessão nova do Claude Code chegar rápido
no mesmo patamar de discussão que foi alcançado num RPA anterior (Python +
PyAutoGUI, envio de NFS-e via CIGAM). Copie-o pra raiz deste projeto novo
como `CLAUDE.md` -- o Claude Code carrega esse arquivo sozinho no início de
toda sessão nesta pasta, sem precisar colar nada manualmente.

O projeto anterior automatizava outro sistema (CIGAM). Este aqui é pra um
sistema diferente. **Nada específico do CIGAM deve vazar pra este projeto**
-- o que segue é só a arquitetura e o jeito de trabalhar, que são genéricos.

## Arquitetura -- três papéis, nunca misturados

- **Mãos** (`paginas/tela.py`, classe `Tela`): só clica, digita e espera a
  tela. Nunca decide nada com base em regra de negócio.
- **Cérebro** (`processo.py`, classe `Processo`): decide a ordem, consulta
  dados, chama a Tela. Nunca toca pixel diretamente.
- **Memória** (`dados/`): todo acesso a dado externo (banco, API, arquivo)
  mora aqui. Se for SQL: sempre bind variables, nunca concatenação de
  string.

Teste prático da regra, que já causou retrabalho real no projeto anterior:
se está prestes a passar um dado de negócio (ex: nome de uma unidade, um
tipo de cliente) pra dentro de `Tela` pra ela decidir algo com isso -- pare.
Quem resolve "dado X implica ação Y" é sempre o `Processo` (ou a config); a
`Tela` recebe só o resultado já resolvido (ex: qual arquivo de imagem
clicar), nunca a matéria-prima da decisão. Isso vale até pra um **valor
padrão de parâmetro** -- um `def clicar(self, imagem=IMG_PADRAO)` dentro da
Tela já é a Tela "sabendo" qual é o caminho normal, o que é a mesma
violação escondida de outro jeito. O padrão também tem que vir de fora.

## O motor de espera (reaproveitar quase sem alteração)

Os métodos de baixo nível de `Tela` não mudam de projeto pra projeto:
`_achar` (match de imagem via PyAutoGUI/OpenCV), `_esperar`/`_sumir`
(espera por evento de tela, nunca por `sleep` fixo -- o tempo real de cada
etapa varia e um fixo é sempre curto ou longo demais), `_visivel` (checagem
sem estourar erro, pra escolher caminho), `_clicar_imagem` (aceita uma
imagem só ou uma tupla de alternativas -- clica na primeira encontrada),
`_digitar`, `_atalho`, `_combo`.

Dois mecanismos genéricos, também reaproveitáveis:

- **`detectar_etapa` / `avancar`**: dado um sistema que pode já estar
  aberto em qualquer estado quando o script começa a rodar (porque o
  processo do robô e o app alvo sobem em paralelo, sem sincronismo -- ver
  a seção de inicialização.bat/scheduler, se existir um), uma sequência
  ordenada de pivôs com a ação necessária pra alcançar cada um a partir do
  anterior. Detecta o pivô mais avançado já visível e roda só as ações que
  faltam. Elimina a necessidade de assumir "sempre começa do zero".
- **`TELAS_CAOTICAS`** (e, se fizer sentido separar por momento do fluxo,
  um segundo catálogo tipo `TELAS_CAOTICAS_<MOMENTO>`): avisos/popups que
  podem aparecer fora de hora. Cada entrada é
  `(imagem_ou_tupla_de_imagens, *passos)` -- tupla na primeira posição
  significa "achar qualquer uma já conta". Cada passo é
  `lambda tela: ...`, executado dentro de um `try/except` próprio (uma
  falha num passo não deve travar os outros nem o robô). Varrido no(s)
  ponto(s) certo(s) do motor de espera -- não espalhado pelo fluxo de
  negócio.

## Imagens de reconhecimento

Sem cadastro manual: salvar o `.png` em `paginas/imagens/` já é o
cadastro. `gerar_imagens.py` roda sozinho a cada execução (chamado por
`tarefas.py` antes de importar a lib de automação) e regenera
`paginas/imagens_geradas.py` com uma constante `IMG_<NOME>` por arquivo
(nome do arquivo em maiúsculas). Nunca editar esse arquivo gerado na mão.

Se um quadro tem uma região que muda (um número, por exemplo) mas o resto
é fixo: apagar essa região deixando transparente (canal alfa) no editor de
imagem, e usar um matching com máscara (`cv2.matchTemplate` com
`mask=`, já que o PyAutoGUI não expõe isso) em vez do match normal.

## Confiabilidade

- Um só tipo de exceção pra falha de tela (`ErroNaTela`) -- o processo é
  uma passada linear, sem fila, então não precisa distinguir "pula esse
  item" de "tenta de novo" com duas classes. Só reconsiderar se o
  processo virar uma fila de verdade.
- Toda exceção fatal capturada por inteiro no ponto de entrada (nunca deixar
  o console fechar sem logar) -- inclusive `KeyboardInterrupt`, que **não**
  herda de `Exception` e precisa de um `except` separado se quiser pausar o
  console em vez de fechar direto no Ctrl+C.
- `max_falhas_seguidas` (ou nome equivalente) limitando quantas vezes
  recuperar-e-tentar-de-novo a mesma unidade de trabalho antes de escalar
  e desistir -- sem isso, um problema estrutural (não um popup avulso)
  recupera pra sempre sem nunca avisar ninguém.
- Se o sistema alvo tiver um jeito de matar o processo à força
  (equivalente a um `EJECTION()`), implementar de verdade -- não deixar a
  chamada comentada "pra depois". Um `except Exception` fatal que não
  garante processo limpo pra próxima execução é uma rede de segurança que
  só existe no papel.

## Como eu (usuário) trabalho com você

- Proponha mudanças não-triviais e espere confirmação antes de editar --
  principalmente decisões de arquitetura. Mudanças pequenas e óbvias
  (renomear, corrigir um import) pode aplicar direto.
- Ao editar algo que já foi discutido/rejeitado antes, mostre a edição
  **inteira** de uma vez (não fragmente em vários tool calls pequenos que
  ficam difíceis de acompanhar).
- Comentário em código é só pra explicar o "porquê" não-óbvio. Nunca deixe
  vazar a deliberação da conversa no comentário (referência a "conforme
  discutido", ao que foi tentado antes, etc.) -- o comentário tem que
  fazer sentido pra quem nunca viu a conversa.
- Nomes de função/variável: prefira vocabulário técnico preciso a
  metáfora/antropomorfização ("detector de estagnação" em vez de "robô
  percebe e segue em frente"). Cuidado com palavras em PT-BR que têm outro
  sentido comum (ex: "mascarado").
- Eu rodo os comandos (pip install, python script.py, git etc.) -- nunca
  execute isso por mim. Só me diga o comando exato.
- O terminal integrado do VS Code já ativa o venv sozinho quando o
  interpretador certo está selecionado -- não sugira ativação manual como
  primeiro passo.
- Se eu pedir um resumo/relatório, posso pedir pra reescrever no mesmo
  conteúdo em registros bem diferentes (bem técnico com nomes de
  classe/método, ou uma frase só acessível, ou estilo telegráfico/particípio
  tipo ata de reunião) -- isso é iteração normal de tom, não indecisão.
- Documento formal pra guardar/compartilhar (manual, requisitos): capriche
  no layout (cores, tabelas, hierarquia tipográfica) em vez de devolver
  texto corrido.
