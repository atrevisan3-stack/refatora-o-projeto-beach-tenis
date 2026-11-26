# language: pt
@relatorios
Funcionalidade: Relatórios de clientes, caixa e grade de quadras
  Como administrador
  Quero consultar a ficha do cliente, o fluxo de caixa, o resumo mensal e a grade do dia
  Para acompanhar o que foi vendido, o que foi pago e o que falta receber

  Contexto:
    Dado que hoje é "12/03/2026"
    E que a tabela de valores tem sauna 30,00, aula 50,00 e os vencimentos:
      | dia | valor  |
      | 10  | 200,00 |
      | 20  | 220,00 |
      | 25  | 250,00 |
    E que existem os clientes:
      | codigo | nome  |
      | 1      | Ana   |
      | 2      | Bruno |
      | 3      | Carla |
    E que existe o produto "Água mineral" de código 2 com preço 5,00

  # --- Ficha do cliente -------------------------------------------------------

  @regra_ficha_cliente
  Cenário: A ficha reúne reservas, histórico e total em aberto
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    E que as mensalidades já foram geradas em "12/03/2026"
    E que o cliente 1 consumiu 2 unidades do produto 2 em "12/03/2026"
    Quando eu consulto a ficha do cliente 1
    Então a ficha deve listar 1 reservas
    E o total em aberto da ficha deve ser 110,00
    E o histórico da ficha deve ter os lançamentos:
      | descricao             | valor  | situacao  |
      | Mensalidade do Squash | 100,00 | em aberto |
      | Água mineral          | 10,00  | em aberto |

  @regra_ficha_cliente
  Cenário: Depois de um pagamento parcial a ficha mostra só o saldo em aberto
    Dado que o cliente 3 consumiu 2 unidades do produto 2 em "12/03/2026"
    E que o cliente 3 pagou 4,00 em "12/03/2026"
    Quando eu consulto a ficha do cliente 3
    Então o total em aberto da ficha deve ser 6,00
    E o histórico da ficha deve ter os lançamentos:
      | descricao          | valor | situacao  |
      | Água mineral       | 10,00 | quitado   |
      | Saldo de pagamento | 6,00  | em aberto |

  @regra_ficha_cliente
  Cenário: Ficha de cliente inexistente é recusada
    Quando eu consulto a ficha do cliente 9
    Então o sistema deve recusar com a mensagem "Código de cliente não cadastrado!"

  # --- Fluxo de caixa ---------------------------------------------------------

  @regra_fluxo_caixa
  Cenário: O fluxo de caixa separa sauna, squash e produtos em pago e em aberto
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    E que as mensalidades já foram geradas em "12/03/2026"
    E que o cliente 3 consumiu 2 unidades do produto 2 em "12/03/2026"
    E que "Diego" já entrou na sauna hoje
    E que o cliente 1 pagou 100,00 em "12/03/2026"
    Quando eu consulto o fluxo de caixa de "12/03/2026"
    Então o fluxo de caixa deve mostrar:
      | categoria | pago   | em_aberto |
      | Sauna     | 0,00   | 30,00     |
      | Squash    | 100,00 | 100,00    |
      | Produtos  | 0,00   | 10,00     |

  @regra_fluxo_caixa
  Cenário: Saldo de pagamento não entra no fluxo de caixa
    Dado que o cliente 3 consumiu 2 unidades do produto 2 em "12/03/2026"
    E que o cliente 3 pagou 4,00 em "12/03/2026"
    Quando eu consulto o fluxo de caixa de "12/03/2026"
    Então o fluxo de caixa deve mostrar:
      | categoria | pago  | em_aberto |
      | Sauna     | 0,00  | 0,00      |
      | Squash    | 0,00  | 0,00      |
      | Produtos  | 10,00 | 0,00      |

  @regra_fluxo_caixa
  Cenário: A sauna entra no caixa pelo valor efetivamente pago
    Dado que "Diego" já entrou na sauna hoje
    E que a conta de "Diego" foi fechada com pagamento de 25,00
    Quando eu consulto o fluxo de caixa de "12/03/2026"
    Então o fluxo de caixa deve mostrar:
      | categoria | pago  | em_aberto |
      | Sauna     | 25,00 | 0,00      |
      | Squash    | 0,00  | 0,00      |
      | Produtos  | 0,00  | 0,00      |

  # --- Resumo mensal ----------------------------------------------------------

  @regra_resumo_mensal @defeito_D03 @defeito_corrigido
  Cenário: O resumo mensal tem uma linha por dia, inclusive o dia 31
    Dado que o cliente 3 consumiu 1 unidades do produto 2 em "31/03/2026"
    Quando eu gero o resumo mensal de 3/2026
    Então o resumo deve ter 31 dias
    E no dia 31 o resumo deve mostrar vendido 5,00, pago 0,00 e a receber 5,00

  @regra_resumo_mensal
  Cenário: O resumo mensal soma o vendido e o pago de cada dia
    Dado que o cliente 3 consumiu 2 unidades do produto 2 em "12/03/2026"
    E que o cliente 3 pagou 10,00 em "12/03/2026"
    E que o cliente 1 consumiu 1 unidades do produto 2 em "12/03/2026"
    Quando eu gero o resumo mensal de 3/2026
    Então no dia 12 o resumo deve mostrar vendido 15,00, pago 10,00 e a receber 5,00
    E no dia 13 o resumo deve mostrar vendido 0,00, pago 0,00 e a receber 0,00

  @regra_resumo_mensal
  Cenário: Fevereiro de ano não bissexto tem 28 dias no resumo
    Quando eu gero o resumo mensal de 2/2026
    Então o resumo deve ter 28 dias

  # --- Grade do dia -----------------------------------------------------------

  @regra_grade_dia
  Cenário: A grade do dia mostra os jogadores e marca as aulas
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    E que existe uma aula na segunda-feira às "10:00" na quadra 2 para os clientes "3"
    Quando eu consulto a grade de "16/03/2026"
    Então na grade o horário "18:00" na quadra 1 deve mostrar "Ana, Bruno"
    E na grade o horário "10:00" na quadra 2 deve mostrar "Carla (AULA)"
    E na grade o horário "18:00" na quadra 2 deve estar livre

  @regra_grade_dia
  Cenário: A grade de outro dia da semana não mostra as reservas de segunda
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu consulto a grade de "17/03/2026"
    Então todos os horários da grade devem estar livres
