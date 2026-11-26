# language: pt
@multas
Funcionalidade: Geração de multas por atraso da mensalidade de jogo
  Como administrador
  Quero gerar multas para quem não pagou a mensalidade de jogo até o vencimento
  Para cobrar a diferença entre as faixas de vencimento

  Contexto:
    Dado que a tabela de valores tem sauna 30,00, aula 50,00 e os vencimentos:
      | dia | valor  |
      | 10  | 200,00 |
      | 20  | 220,00 |
      | 25  | 250,00 |
    E que existem os clientes:
      | codigo | nome  |
      | 1      | Ana   |
      | 2      | Bruno |
      | 3      | Carla |
    E que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"

  @regra_primeira_multa
  Cenário: Primeira multa entre o segundo e o terceiro vencimento
    Quando eu gero as multas em "22/03/2026"
    Então devem ser geradas 2 cobranças
    E o cliente 1 deve ter uma multa de código -2 no valor de 10,00
    E o cliente 2 deve ter uma multa de código -2 no valor de 10,00

  @regra_segunda_multa
  Cenário: Segunda multa a partir do terceiro vencimento
    Quando eu gero as multas em "26/03/2026"
    Então devem ser geradas 2 cobranças
    E o cliente 1 deve ter uma multa de código -3 no valor de 15,00

  @regra_periodo_multa
  Cenário: Multas fora do período de cobrança são recusadas
    Quando eu gero as multas em "15/03/2026"
    Então o sistema deve recusar com a mensagem "As multas não foram geradas porque está fora do período correto!"
    E o cliente 1 não deve ter multas

  @regra_multa_unica_no_mes
  Cenário: A mesma multa não é gerada duas vezes no mês
    Dado que as multas já foram geradas em "22/03/2026"
    Quando eu gero as multas em "23/03/2026"
    Então o sistema deve recusar com a mensagem "As multas deste mês já foram geradas!"

  @defeito_D01 @defeito_corrigido
  Cenário: D01 corrigido - a primeira multa não impede a segunda no mesmo mês
    Dado que as multas já foram geradas em "22/03/2026"
    Quando eu gero as multas em "26/03/2026"
    Então devem ser geradas 2 cobranças
    E o cliente 1 deve ter uma multa de código -2 no valor de 10,00
    E o cliente 1 deve ter uma multa de código -3 no valor de 15,00

  @regra_mensalidade_paga_isenta
  Cenário: Cliente que pagou a mensalidade do mês não recebe multa
    Dado que o cliente 1 pagou a mensalidade de "15/03/2026"
    Quando eu gero as multas em "22/03/2026"
    Então devem ser geradas 1 cobranças
    E o cliente 1 não deve ter multas
    E o cliente 2 deve ter uma multa de código -2 no valor de 10,00

  @regra_aula_sem_multa
  Cenário: Reservas de aula não recebem multa
    Dado que existe uma aula na terça-feira às "10:00" na quadra 2 para os clientes "3"
    Quando eu gero as multas em "22/03/2026"
    Então devem ser geradas 2 cobranças
    E o cliente 3 não deve ter multas
