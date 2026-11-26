# language: pt
@mensalidades
Funcionalidade: Geração de mensalidades de squash
  Como administrador
  Quero gerar as mensalidades do mês a partir da grade de reservas
  Para cobrar cada cliente pelo seu horário

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

  @regra_rateio_jogo
  Cenário: Mensalidade de jogo é rateada entre os jogadores pelo valor da primeira faixa
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu gero as mensalidades em "12/03/2026"
    Então devem ser geradas 2 cobranças
    E o cliente 1 deve ter uma mensalidade de 100,00
    E o cliente 2 deve ter uma mensalidade de 100,00

  # Março/2026 tem 5 terças-feiras: 5 aulas × 50,00 (RN23).
  @regra_aulas_do_mes
  Cenário: Mensalidade de aula vale o número de aulas do mês
    Dado que existe uma aula na terça-feira às "10:00" na quadra 2 para os clientes "3"
    Quando eu gero as mensalidades em "12/03/2026"
    Então devem ser geradas 1 cobranças
    E o cliente 3 deve ter uma mensalidade de 250,00

  @regra_geracao_idempotente
  Cenário: Gerar mensalidades duas vezes no mesmo mês não duplica cobranças
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    E que as mensalidades já foram geradas em "05/03/2026"
    Quando eu gero as mensalidades em "12/03/2026"
    Então devem ser geradas 0 cobranças
    E o cliente 1 deve ter 1 lançamentos de mensalidade

  @regra_geracao_idempotente
  Cenário: Um novo mês gera novas mensalidades
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    E que as mensalidades já foram geradas em "12/03/2026"
    Quando eu gero as mensalidades em "12/04/2026"
    Então devem ser geradas 2 cobranças
    E o cliente 1 deve ter 2 lançamentos de mensalidade

  @regra_valores_configurados
  Cenário: Não é possível gerar mensalidades sem a tabela de valores
    Dado que a tabela de valores não foi configurada
    E que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu gero as mensalidades em "12/03/2026"
    Então o sistema deve recusar com a mensagem "Configure os valores antes de gerar mensalidades ou multas."
