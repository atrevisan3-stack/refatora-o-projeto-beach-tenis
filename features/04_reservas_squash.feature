# language: pt
@reservas_squash
Funcionalidade: Reserva semanal de horários de squash
  Como atendente
  Quero reservar quadras de squash para jogos e aulas
  Para organizar a grade semanal e gerar as mensalidades

  Contexto:
    Dado que existem os clientes:
      | codigo | nome  |
      | 1      | Ana   |
      | 2      | Bruno |
      | 3      | Carla |

  Cenário: Reservar um jogo para vários clientes
    Quando eu reservo um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Então a operação deve ser aceita
    E deve existir 1 reserva na grade

  Cenário: Reservar uma aula para um único cliente
    Quando eu reservo uma aula na quarta-feira às "10:00" na quadra 2 para os clientes "3"
    Então a operação deve ser aceita
    E deve existir 1 reserva na grade

  @regra_aula_individual
  Cenário: Aula só pode ter um cliente
    Quando eu reservo uma aula na quarta-feira às "10:00" na quadra 2 para os clientes "1,2"
    Então o sistema deve recusar com a mensagem "A reserva de uma quadra para aula deve ser feita para somente um cliente!"
    E deve existir 0 reserva na grade

  @regra_validacao_reserva
  Esquema do Cenário: Dados inválidos da reserva são recusados
    Quando eu reservo um jogo <dia> às "<horario>" na quadra <quadra> para os clientes "<clientes>"
    Então o sistema deve recusar com a mensagem "<mensagem>"

    Exemplos:
      | dia              | horario | quadra | clientes | mensagem                                              |
      | no domingo       | 18:00   | 1      | 1,2      | O dia da reserva deve ser de segunda-feira a sábado!  |
      | na sexta-feira   | 18:00   | 4      | 1,2      | A quadra deve ser 1, 2 ou 3!                          |
      | na sexta-feira   | 18:30   | 1      | 1,2      | O horário da reserva é inválido!                      |
      | na sexta-feira   | 18:00   | 1      |          | A reserva deve ter ao menos um cliente!               |
      | na sexta-feira   | 18:00   | 1      | 1,0      | O cliente da reserva deve estar cadastrado!           |
      | na sexta-feira   | 18:00   | 1      | 2,2      | Este cliente já foi incluído nesta reserva!              |

  @regra_substituicao_confirmada
  Cenário: Substituir uma reserva ocupada exige confirmação
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu reservo uma aula na segunda-feira às "18:00" na quadra 1 para os clientes "3"
    Então o sistema deve recusar com a mensagem "Já existe uma reserva para este horário; confirme a substituição."
    E a reserva da segunda-feira às "18:00" na quadra 1 deve ser dos clientes "1,2"

  @regra_substituicao_confirmada
  Cenário: Substituir uma reserva ocupada com confirmação
    Dado que existe um jogo na segunda-feira às "18:00" na quadra 1 para os clientes "1,2"
    Quando eu confirmo a substituição por uma aula na segunda-feira às "18:00" na quadra 1 para os clientes "3"
    Então a operação deve ser aceita
    E deve existir 1 reserva na grade
    E a reserva da segunda-feira às "18:00" na quadra 1 deve ser dos clientes "3"
