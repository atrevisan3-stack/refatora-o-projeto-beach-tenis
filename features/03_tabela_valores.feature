# language: pt
@tabela_valores
Funcionalidade: Tabela de valores e vencimentos
  Como administrador
  Quero configurar o preço da sauna, da aula e as faixas de vencimento da mensalidade
  Para que mensalidades e multas sejam calculadas automaticamente

  Cenário: Salvar uma tabela de valores com três faixas de vencimento
    Quando eu salvo a tabela de valores com sauna 30,00, aula 50,00 e os vencimentos:
      | dia | valor  |
      | 10  | 200,00 |
      | 20  | 220,00 |
      | 25  | 250,00 |
    Então a operação deve ser aceita
    E a tabela de valores deve ter 3 faixas de vencimento

  Cenário: Apenas a primeira faixa de vencimento é obrigatória
    Quando eu salvo a tabela de valores com sauna 30,00, aula 50,00 e os vencimentos:
      | dia | valor  |
      | 10  | 200,00 |
    Então a operação deve ser aceita
    E a tabela de valores deve ter 1 faixas de vencimento

  @regra_validacao_valores
  Esquema do Cenário: Valores inválidos são recusados e nada é gravado
    Quando eu salvo a tabela de valores com sauna <sauna>, aula <aula> e os vencimentos:
      | dia    | valor    |
      | <dia1> | <valor1> |
      | <dia2> | <valor2> |
    Então o sistema deve recusar com a mensagem "<mensagem>"
    E nenhuma tabela de valores deve estar gravada

    Exemplos:
      | sauna | aula  | dia1 | valor1 | dia2 | valor2 | mensagem                                              |
      | 0,00  | 50,00 | 10   | 200,00 | 20   | 220,00 | O valor da sauna deve ser maior que zero!             |
      | 30,00 | 0,00  | 10   | 200,00 | 20   | 220,00 | O valor da aula deve ser maior que zero!              |
      | 30,00 | 50,00 | 0    | 200,00 | 20   | 220,00 | Os vencimentos devem estar entre os dias 1 e 28.      |
      | 30,00 | 50,00 | 10   | 200,00 | 29   | 220,00 | Os vencimentos devem estar entre os dias 1 e 28.      |
      | 30,00 | 50,00 | 10   | 200,00 | 10   | 220,00 | Os vencimentos devem ser diferentes.                  |
      | 30,00 | 50,00 | 10   | 200,00 | 20   | vazio  | Dia e valor do vencimento devem ser informados juntos. |
      | 30,00 | 50,00 | 10   | 200,00 | 20   | 0,00   | O valor da mensalidade deve ser maior que zero.       |
