# language: pt
@backup
Funcionalidade: Backup das tabelas
  Como administrador
  Quero exportar as tabelas do banco para uma pasta
  Para guardar uma cópia dos dados com a data e a hora da exportação

  @regra_backup
  Cenário: O backup usa a data e a hora atuais no nome dos arquivos
    Dado que hoje é "12/03/2026"
    E que existe uma pasta para o backup
    Quando eu faço o backup nessa pasta
    Então a operação deve ser aceita
    E o backup deve gerar o arquivo "clientes_20260312_103000.csv"

  @regra_backup
  Cenário: Outro dia gera outro carimbo
    Dado que hoje é "01/04/2026"
    E que existe uma pasta para o backup
    Quando eu faço o backup nessa pasta
    Então o backup deve gerar o arquivo "clientes_20260401_103000.csv"

  @regra_backup
  Cenário: Backup em pasta inexistente é recusado
    Quando eu faço o backup na pasta "C:/pasta-que-nao-existe-dante"
    Então o sistema deve recusar com a mensagem "Selecione uma pasta existente para o backup."
    E nenhuma exportação deve ter sido feita
