# language: pt
@cadastro_clientes
Funcionalidade: Cadastro de clientes
  Como atendente do Dante Squash & Sauna
  Quero cadastrar e editar clientes
  Para poder registrar reservas, consumos e pagamentos em nome deles

  @regra_codigo_automatico
  Cenário: Cadastrar um cliente novo gera o próximo código disponível
    Dado que já existe o cliente "Ana Souza" com código 1
    Quando eu cadastro o cliente "Bruno Lima" com CPF "12345678901" e telefone "54999990000"
    Então o cliente "Bruno Lima" deve estar cadastrado com código 2
    E devem existir 2 clientes cadastrados

  @regra_edicao
  Cenário: Editar um cliente existente mantém o código
    Dado que já existe o cliente "Ana Souza" com código 1
    Quando eu altero o nome do cliente de código 1 para "Ana Souza Pereira"
    Então o cliente "Ana Souza Pereira" deve estar cadastrado com código 1
    E devem existir 1 clientes cadastrados

  @regra_nome_obrigatorio
  Cenário: Nome do cliente é obrigatório
    Quando eu cadastro o cliente "   " com CPF "" e telefone ""
    Então o sistema deve recusar com a mensagem "O nome do cliente deve ser informado!"
    E devem existir 0 clientes cadastrados

  @regra_tamanho_campos
  Esquema do Cenário: Campos do cliente respeitam o tamanho máximo
    Quando eu cadastro um cliente com nome de <tamanho_nome> caracteres e CPF "<cpf>"
    Então o sistema deve recusar com a mensagem "<mensagem>"

    Exemplos:
      | tamanho_nome | cpf          | mensagem                                           |
      | 51           |              | O nome do cliente deve ter no máximo 50 caracteres! |
      | 10           | 123456789012 | O CPF deve ter no máximo 11 caracteres!             |

  @regra_tamanho_campos
  Cenário: Nome com exatamente 50 caracteres é aceito
    Quando eu cadastro um cliente com nome de 50 caracteres e CPF ""
    Então a operação deve ser aceita
    E devem existir 1 clientes cadastrados
