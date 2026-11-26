# language: pt
@cadastro_produtos
Funcionalidade: Cadastro de produtos
  Como administrador
  Quero manter os produtos vendidos no bar e na sauna
  Para que os consumos sejam cobrados pelo preço correto

  # A tela envia código 0 para um produto novo, como faz para clientes.
  # Product.validate() recusa o código 0 antes de o serviço gerar o próximo código.
  # O cenário falha até a correção na camada de domínio/serviço (itens 1 e 2).
  @regra_codigo_automatico @defeito_encontrado
  Cenário: Cadastrar um produto válido
    Quando eu cadastro o produto "Água mineral" com preço 5,00 e unidade "un"
    Então o produto "Água mineral" deve estar cadastrado com código 2 e preço 5,00

  @regra_validacao_produto
  Esquema do Cenário: Dados inválidos do produto são recusados
    Quando eu cadastro o produto "<descricao>" com preço <preco> e unidade "<unidade>"
    Então o sistema deve recusar com a mensagem "<mensagem>"

    Exemplos:
      | descricao     | preco | unidade | mensagem                                     |
      |               | 5,00  | un      | A descrição do produto deve ser informada!   |
      | Refrigerante  | 0,00  | un      | O preço do produto deve ser maior que zero!  |
      | Refrigerante  | -1,00 | un      | O preço do produto deve ser maior que zero!  |
      | Refrigerante  | 6,00  |         | A unidade do produto deve ser informada!     |

  @regra_codigos_internos
  Esquema do Cenário: Códigos 0 e 1 são reservados para uso interno
    Quando eu cadastro o produto de código <codigo> "Produto qualquer" com preço 3,00 e unidade "un"
    Então o sistema deve recusar com a mensagem "Os códigos 0 e 1 são de uso interno da aplicação!"

    Exemplos:
      | codigo |
      | 0      |
      | 1      |
