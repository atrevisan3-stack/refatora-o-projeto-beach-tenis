# language: pt
@sauna
Funcionalidade: Controle diário de frequentadores da sauna
  Como atendente da sauna
  Quero registrar a entrada, os consumos e o fechamento da conta de cada frequentador
  Para cobrar a sauna no mesmo dia

  Contexto:
    Dado que hoje é "12/03/2026"
    E que a tabela de valores tem sauna 30,00, aula 50,00 e os vencimentos:
      | dia | valor  |
      | 10  | 200,00 |
    E que existe o produto "Água mineral" de código 2 com preço 5,00

  @regra_entrada_sauna
  Cenário: Registrar a entrada lança o valor da sauna na conta
    Quando eu registro a entrada de "Carla" na sauna em "12/03/2026"
    Então a operação deve ser aceita
    E a conta de "Carla" na sauna deve totalizar 30,00
    E a conta de "Carla" na sauna deve estar aberta

  @regra_nome_unico_sauna
  Cenário: Nome do frequentador deve ser único no dia, sem diferenciar maiúsculas
    Dado que "Carla" já entrou na sauna hoje
    Quando eu registro a entrada de "CARLA" na sauna em "12/03/2026"
    Então o sistema deve recusar com a mensagem "O nome do cliente deve ser diferente de outro cliente da sauna!"

  @regra_nome_unico_sauna
  Cenário: Nome do frequentador é obrigatório
    Quando eu registro a entrada de "  " na sauna em "12/03/2026"
    Então o sistema deve recusar com a mensagem "O nome do cliente deve ser informado!"

  @regra_consumo_sauna
  Cenário: Consumo de produtos soma na conta do frequentador
    Dado que "Carla" já entrou na sauna hoje
    Quando "Carla" consome 2 unidades do produto 2 na sauna
    Então a conta de "Carla" na sauna deve totalizar 40,00

  @regra_fechamento_sauna
  Cenário: Fechar a conta quita todos os lançamentos
    Dado que "Carla" já entrou na sauna hoje
    E que "Carla" consumiu 2 unidades do produto 2 na sauna
    Quando eu fecho a conta de "Carla" com pagamento de 40,00
    Então a conta de "Carla" na sauna deve estar fechada
    E a conta de "Carla" na sauna deve totalizar 40,00

  @regra_fechamento_sauna
  Cenário: Diferença no fechamento é ajustada na entrada
    Dado que "Carla" já entrou na sauna hoje
    E que "Carla" consumiu 2 unidades do produto 2 na sauna
    Quando eu fecho a conta de "Carla" com pagamento de 35,00
    Então a conta de "Carla" na sauna deve estar fechada
    E a conta de "Carla" na sauna deve totalizar 35,00

  @regra_conta_fechada
  Cenário: Conta fechada não aceita novos consumos
    Dado que "Carla" já entrou na sauna hoje
    E que a conta de "Carla" foi fechada com pagamento de 30,00
    Quando "Carla" consome 1 unidades do produto 2 na sauna
    Então o sistema deve recusar com a mensagem "A conta do frequentador já foi finalizada."

  @regra_fechamento_sauna
  Cenário: Fechamento sem valor é recusado
    Dado que "Carla" já entrou na sauna hoje
    Quando eu fecho a conta de "Carla" com pagamento de 0,00
    Então o sistema deve recusar com a mensagem "O valor a ser pago deve ser informado!"
    E a conta de "Carla" na sauna deve estar aberta

  @regra_somente_hoje
  Cenário: Só é possível alterar a sauna do dia de hoje
    Quando eu registro a entrada de "Diego" na sauna em "11/03/2026"
    Então o sistema deve recusar com a mensagem "Só é possível alterar os dados da sauna para o dia de hoje."

  @regra_frequentador_existente
  Cenário: Consumo para frequentador inexistente é recusado
    Quando "Diego" consome 1 unidades do produto 2 na sauna
    Então o sistema deve recusar com a mensagem "Frequentador da sauna não encontrado."
