# language: pt
@consumo_produtos
Funcionalidade: Registro de consumo de produtos por cliente
  Como atendente do bar
  Quero lançar os produtos consumidos na conta do cliente
  Para cobrá-los no próximo pagamento

  Contexto:
    Dado que existem os clientes:
      | codigo | nome |
      | 1      | Ana  |
    E que existe o produto "Água mineral" de código 2 com preço 5,00

  Cenário: Lançar consumo de produto para cliente cadastrado
    Quando eu lanço 3 unidades do produto 2 para o cliente 1 em "12/03/2026"
    Então a operação deve ser aceita
    E o cliente 1 deve ter um débito em aberto de 15,00

  Cenário: Consumos do mesmo dia recebem sequências diferentes
    Quando eu lanço 1 unidades do produto 2 para o cliente 1 em "12/03/2026"
    E eu lanço 2 unidades do produto 2 para o cliente 1 em "12/03/2026"
    Então os consumos do cliente 1 devem ter as sequências "1,2"
    E o cliente 1 deve ter um débito em aberto de 15,00

  @regra_validacao_consumo
  Esquema do Cenário: Consumos inválidos são recusados
    Quando eu lanço <quantidade> unidades do produto <produto> para o cliente <cliente> em "12/03/2026"
    Então o sistema deve recusar com a mensagem "<mensagem>"
    E o cliente 1 deve ter um débito em aberto de 0,00

    Exemplos:
      | cliente | produto | quantidade | mensagem                                   |
      | 0       | 2       | 1          | O cliente deve ser informado!              |
      | 9       | 2       | 1          | Código de cliente não cadastrado!          |
      | 1       | 2       | 0          | A quantidade do Produto deve ser informada! |
      | 1       | 1       | 1          | O produto consumido deve estar cadastrado! |
      | 1       | 99      | 1          | O produto consumido deve estar cadastrado! |
