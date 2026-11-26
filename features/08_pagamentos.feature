# language: pt
@pagamentos
Funcionalidade: Pagamento de débitos do cliente
  Como atendente
  Quero registrar pagamentos totais ou parciais, com desconto opcional
  Para quitar os consumos e manter o saldo restante em aberto

  Contexto:
    Dado que existem os clientes:
      | codigo | nome |
      | 1      | Ana  |
    E que existe o produto "Raquete alugada" de código 2 com preço 50,00
    E que o cliente 1 consumiu 2 unidades do produto 2 em "01/03/2026"

  Cenário: Consultar o total em aberto
    Então o total devido pelo cliente 1 deve ser 100,00

  @regra_pagamento_total
  Cenário: Pagamento total quita todos os consumos
    Quando o cliente 1 paga 100,00 com desconto de 0,00 em "20/03/2026"
    Então o pagamento deve ser registrado como total
    E o total devido pelo cliente 1 deve ser 0,00
    E deve existir 1 pagamento registrado de 100,00 para o cliente 1

  @regra_pagamento_parcial
  Cenário: Pagamento parcial quita os consumos e lança o saldo restante
    Quando o cliente 1 paga 60,00 com desconto de 0,00 em "20/03/2026"
    Então o pagamento deve ser registrado como parcial
    E o saldo do pagamento deve ser 40,00
    E o total devido pelo cliente 1 deve ser 40,00
    E deve existir um lançamento de ajuste de 40,00 em aberto para o cliente 1

  @regra_desconto
  Cenário: Desconto completa o pagamento e é lançado como crédito quitado
    Quando o cliente 1 paga 90,00 com desconto de 10,00 em "20/03/2026"
    Então o pagamento deve ser registrado como total
    E o total devido pelo cliente 1 deve ser 0,00
    E deve existir um lançamento de ajuste de -10,00 quitado para o cliente 1

  @regra_valor_obrigatorio
  Cenário: Pagamento sem valor é recusado e nada é alterado
    Quando o cliente 1 paga 0,00 com desconto de 0,00 em "20/03/2026"
    Então o sistema deve recusar com a mensagem "O valor a ser pago deve ser informado!"
    E o total devido pelo cliente 1 deve ser 100,00
    E não deve existir pagamento registrado

  @regra_cliente_obrigatorio
  Cenário: Pagamento exige um cliente informado
    Quando o cliente 0 paga 50,00 com desconto de 0,00 em "20/03/2026"
    Então o sistema deve recusar com a mensagem "O cliente deve ser informado!"
