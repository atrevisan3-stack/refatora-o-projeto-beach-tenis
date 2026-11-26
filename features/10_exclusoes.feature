# language: pt
@exclusoes
Funcionalidade: Exclusão de cadastros e lançamentos
  Como administrador
  Quero excluir clientes, produtos, consumos, reservas e frequentadores da sauna
  Sem apagar nada que já tenha movimentação ou que seja de uso interno

  Contexto:
    Dado que hoje é "12/03/2026"
    E que a tabela de valores tem sauna 30,00, aula 50,00 e os vencimentos:
      | dia | valor  |
      | 10  | 200,00 |
    E que existem os clientes:
      | codigo | nome  |
      | 1      | Ana   |
      | 2      | Bruno |
    E que existe o produto "Água mineral" de código 2 com preço 5,00
    E que existe o produto "Refrigerante" de código 3 com preço 7,00

  # --- Clientes ---------------------------------------------------------------

  @regra_exclusao_cliente
  Cenário: Excluir um cliente sem movimentação
    Quando eu excluo o cliente 2
    Então a operação deve ser aceita
    E devem existir 1 clientes cadastrados

  @regra_exclusao_cliente
  Cenário: Cliente com consumo não pode ser excluído
    Dado que o cliente 1 consumiu 1 unidades do produto 2 em "12/03/2026"
    Quando eu excluo o cliente 1
    Então o sistema deve recusar com a mensagem "Este cliente foi utilizado em consumos, pagamentos ou reservas e não pode ser excluído!"
    E devem existir 2 clientes cadastrados

  @regra_exclusao_cliente
  Cenário: Cliente com reserva não pode ser excluído
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu excluo o cliente 2
    Então o sistema deve recusar com a mensagem "Este cliente foi utilizado em consumos, pagamentos ou reservas e não pode ser excluído!"

  @regra_exclusao_cliente @regra_codigos_internos
  Cenário: O cliente interno da sauna não pode ser excluído
    Quando eu excluo o cliente 0
    Então o sistema deve recusar com a mensagem "O cliente 0 é de uso interno da sauna!"

  @regra_exclusao_cliente
  Cenário: Excluir cliente inexistente é recusado
    Quando eu excluo o cliente 9
    Então o sistema deve recusar com a mensagem "Código de cliente não cadastrado!"

  # --- Produtos ---------------------------------------------------------------

  @regra_exclusao_produto
  Cenário: Excluir um produto que nunca foi consumido
    Quando eu excluo o produto 3
    Então a operação deve ser aceita
    E o produto "Refrigerante" não deve estar cadastrado

  @regra_exclusao_produto
  Cenário: Produto já consumido não pode ser excluído
    Dado que o cliente 1 consumiu 1 unidades do produto 2 em "12/03/2026"
    Quando eu excluo o produto 2
    Então o sistema deve recusar com a mensagem "Este produto foi utilizado em consumos e não pode ser excluído!"

  @regra_exclusao_produto @regra_codigos_internos
  Esquema do Cenário: Produtos internos não podem ser excluídos
    Quando eu excluo o produto <codigo>
    Então o sistema deve recusar com a mensagem "Os códigos 0 e 1 são de uso interno da aplicação!"

    Exemplos:
      | codigo |
      | 0      |
      | 1      |
      | -1     |

  @regra_exclusao_produto
  Cenário: Excluir produto inexistente é recusado
    Quando eu excluo o produto 9
    Então o sistema deve recusar com a mensagem "Código de produto não cadastrado!"

  # --- Consumos ---------------------------------------------------------------

  @regra_exclusao_consumo
  Cenário: Excluir um consumo em aberto
    Dado que o cliente 1 consumiu 2 unidades do produto 2 em "12/03/2026"
    Quando eu excluo o consumo de sequência 1 do cliente 1 em "12/03/2026"
    Então a operação deve ser aceita
    E o cliente 1 deve ter um débito em aberto de 0,00

  @regra_exclusao_consumo
  Cenário: Consumo já pago não pode ser excluído
    Dado que o cliente 1 consumiu 2 unidades do produto 2 em "12/03/2026"
    E que o cliente 1 pagou 10,00 em "12/03/2026"
    Quando eu excluo o consumo de sequência 1 do cliente 1 em "12/03/2026"
    Então o sistema deve recusar com a mensagem "Este consumo já foi pago e não pode ser mais excluído!"

  @regra_exclusao_consumo
  Cenário: Excluir consumo inexistente é recusado
    Quando eu excluo o consumo de sequência 5 do cliente 1 em "12/03/2026"
    Então o sistema deve recusar com a mensagem "Consumo não encontrado!"

  # --- Reservas ---------------------------------------------------------------

  @regra_exclusao_reserva
  Cenário: Excluir uma reserva libera o horário
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu excluo a reserva na segunda-feira às "18:00" na quadra 1
    Então a operação deve ser aceita
    E deve existir 0 reserva na grade

  @regra_exclusao_reserva
  Cenário: Excluir reserva inexistente é recusado
    Quando eu excluo a reserva na terça-feira às "10:00" na quadra 2
    Então o sistema deve recusar com a mensagem "Reserva não encontrada!"

  # --- Sauna ------------------------------------------------------------------

  @regra_exclusao_sauna
  Cenário: Remover um frequentador com a conta aberta
    Dado que "Diego" já entrou na sauna hoje
    E que "Diego" consumiu 1 unidades do produto 2 na sauna
    Quando eu removo "Diego" da sauna
    Então a operação deve ser aceita
    E não deve existir conta de "Diego" na sauna

  @regra_exclusao_sauna
  Cenário: Excluir um consumo de produto da conta da sauna
    Dado que "Diego" já entrou na sauna hoje
    E que "Diego" consumiu 2 unidades do produto 2 na sauna
    Quando eu excluo o consumo de sequência 2 da conta de "Diego" na sauna
    Então a operação deve ser aceita
    E a conta de "Diego" na sauna deve totalizar 30,00

  @regra_exclusao_sauna
  Cenário: A entrada da sauna não pode ser excluída
    Dado que "Diego" já entrou na sauna hoje
    Quando eu excluo o consumo de sequência 1 da conta de "Diego" na sauna
    Então o sistema deve recusar com a mensagem "A entrada da sauna não pode ser excluída!"

  @regra_exclusao_sauna
  Cenário: Conta fechada não permite remover o frequentador
    Dado que "Diego" já entrou na sauna hoje
    E que a conta de "Diego" foi fechada com pagamento de 30,00
    Quando eu removo "Diego" da sauna
    Então o sistema deve recusar com a mensagem "A conta deste frequentador já foi encerrada!"
