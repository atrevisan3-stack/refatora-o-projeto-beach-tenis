# Dante Squash & Sauna — refatoração Python

## Relatório

Este trabalho cria uma implementação Python orientada a objetos do núcleo do
Dante Squash & Sauna, mantendo o código Java original em `src/` como referência.
O PDF anexado descreve 18 requisitos funcionais, 30 regras de negócio, a
arquitetura em camadas e defeitos de comportamento que devem ser preservados até
validação pelo cliente.

### Arquitetura aplicada

- **Domínio** (`dante_squash/domain.py`): entidades imutáveis, valores monetários
  como `Decimal`, validações e regras sem dependência de interface ou banco.
- **Aplicação** (`dante_squash/services/`): casos de uso para cadastros, consumo,
  pagamentos, sauna, reservas e geração de mensalidades/multas.
- **Portas** (`dante_squash/ports.py`): protocolos pequenos para repositórios e
  unidade de trabalho.
- **Infraestrutura** (`dante_squash/infrastructure/postgres.py`): adaptador
  PostgreSQL com consultas parametrizadas e transação por caso de uso.
- **Apresentação** (`dante_squash/presentation/tk_app.py`): interface desktop
  Tkinter; ela chama serviços e não contém cálculos de negócio.

As alterações seguem as recomendações do PDF: remoção de dependência de Swing
nas regras, inversão de dependências, segregação de interfaces, consultas
parametrizadas, recursos de banco limitados ao escopo da conexão e operações
atômicas para pagamentos e cobranças. O esquema e os valores monetários no
banco permanecem compatíveis com o legado (`INTEGER` para datas DDMMAAAA e
`DOUBLE PRECISION` para valores); os tipos novos são usados no domínio para
reduzir conversões espalhadas. Uma migração de esquema para `DATE`/`NUMERIC`
deve ser planejada e validada separadamente sobre uma cópia anonimizada.

### Funcionalidades Python nesta etapa

- Cadastro/edição de clientes, produtos e tabela de valores.
- Reservas semanais de squash, com confirmação antes de substituir horário.
- Geração idempotente de mensalidades e geração de multas para reservas de jogo.
- Registro de consumo de produtos por cliente e pagamentos totais/parciais,
  incluindo desconto e saldo.
- Entrada, consumo de produtos e fechamento de conta de frequentadores da sauna.
- Criação segura das oito tabelas e da carga padrão, somente quando ausentes.

Esta é uma migração inicial do núcleo e dos fluxos operacionais principais, não
uma cópia visual tela a tela das 87 classes Java. A interface Python ainda não
inclui a ficha do cliente, relatórios de fluxo/resumo mensal, exclusão de
cadastros, backup/restauração nem administração manual do esquema. O menu Java
original continua disponível em `src/` enquanto esses fluxos são migrados.

### Comportamentos legados deliberadamente caracterizados

Os defeitos D01, D02, D04 e D05 identificados no PDF não foram corrigidos nesta
etapa:

- D01: a existência da primeira multa impede gerar a segunda multa no mesmo mês.
- D02: a leitura de datas de sete dígitos mantém o cálculo incorreto de mês/ano
  nas verificações legadas de mensalidade/multa.
- D04: o resultado do pagamento mantém comparação IEEE-754 (`double`) exata.
- D05: `NaN` continua passando pela validação legado do valor pago.

Esses comportamentos têm testes de caracterização. Alterá-los deve ser uma
decisão separada, com aprovação da regra esperada e teste de regressão.

## Executar pelo código-fonte (Windows e MariaDB)

Cada integrante precisa ter Git (ou receber uma cópia atualizada do projeto),
Python 3.10 ou superior, o servidor MariaDB ativo e acesso a um banco MariaDB.
O pgAdmin é para PostgreSQL; para MariaDB use o cliente MariaDB ou outra
ferramenta compatível.

### 1. Preparar o banco

Se cada integrante tiver MariaDB instalado na própria máquina, abra o cliente
MariaDB como administrador (`root`) e crie um banco e usuário locais:

```sql
CREATE DATABASE IF NOT EXISTS dante_squash
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'dante_app'@'localhost'
  IDENTIFIED BY 'DEFINA_UMA_SENHA_FORTE';

GRANT ALL PRIVILEGES ON dante_squash.* TO 'dante_app'@'localhost';
```

Troque `DEFINA_UMA_SENHA_FORTE` antes de executar. Não use a conta `root` na
aplicação e não compartilhe credenciais pelo chat, e-mail ou repositório.

Para a equipe compartilhar um único banco, o MariaDB deve estar em um
computador/servidor acessível a todos. O administrador precisa criar uma conta
MariaDB para cada integrante, autorizada apenas a partir do endereço de rede
daquele integrante, conceder acesso somente a `dante_squash` e liberar a porta
3306 apenas na rede confiável. Nesse caso, substitua `localhost` pelo endereço
do servidor no DSN. **Não exponha a porta 3306 à internet.**

### 2. Baixar/abrir o projeto e instalar dependências

No VS Code, abra a pasta do projeto. Abra **Terminal > Novo Terminal**, escolha
PowerShell e mude para a pasta raiz do projeto (onde ficam `README.md` e
`requirements.txt`). No computador do autor, por exemplo:

```powershell
Set-Location C:\Users\Acer\Desktop\DanteSquash
Test-Path .\requirements.txt
```

`Test-Path` deve retornar `True`. Cada colega deve substituir o caminho acima
pela pasta onde clonou ou descompactou o projeto. Não execute os comandos a
partir de `C:\Windows\System32`.

Crie um ambiente virtual e instale as dependências. A ativação do ambiente não
é necessária:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configurar a conexão e iniciar

Cole o bloco abaixo no **mesmo terminal PowerShell**. Quando solicitado, digite
a senha criada para `dante_app`; a senha não será exibida nem ficará gravada no
histórico do terminal. Este exemplo conecta ao MariaDB da própria máquina:

```powershell
$env:DANTE_SQUASH_DATABASE = "mariadb"
$secure = Read-Host "Senha do usuario dante_app" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)

try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $encoded = [Uri]::EscapeDataString($password)
    $env:DANTE_SQUASH_MARIADB_DSN = "mysql://dante_app:${encoded}@localhost:3306/dante_squash"
    .\.venv\Scripts\python.exe -m dante_squash
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    Remove-Item Env:DANTE_SQUASH_MARIADB_DSN -ErrorAction SilentlyContinue
    Remove-Variable password,encoded,secure,pointer -ErrorAction SilentlyContinue
}
```

Se a equipe usa um banco compartilhado, altere `localhost` no DSN para o nome
ou endereço do servidor MariaDB e use o usuário/senha individual fornecido pelo
administrador. O servidor precisa aceitar conexões daquela rede.

Ao fechar o aplicativo ou abrir outro terminal, execute novamente o bloco para
definir a conexão nessa sessão. Na primeira execução, a aplicação cria as
tabelas que estiverem ausentes e insere registros padrão. Ela não cria o banco,
não converte dados PostgreSQL existentes e não altera as estruturas das tabelas
que já existem. Faça backup e confirme o banco antes de iniciar.

Para confirmar a criação, conecte ao banco `dante_squash` pelo cliente MariaDB
e execute:

```sql
SHOW TABLES;
```

Para PostgreSQL, configure `DANTE_SQUASH_DATABASE=postgresql` e
`DANTE_SQUASH_DSN` conforme o formato aceito pelo psycopg. Nunca grave DSNs ou
credenciais no código-fonte.

## Gerar executável Windows

O executável não inclui o servidor MariaDB nem credenciais. Configure
`DANTE_SQUASH_DATABASE=mariadb` e `DANTE_SQUASH_MARIADB_DSN` no Windows da
máquina que vai executar o aplicativo. Para compilar em um ambiente Windows:

```powershell
py -m pip install -r requirements-build.txt
py -m PyInstaller --noconfirm --windowed --onefile --name DanteSquash --collect-submodules dante_squash dante_squash\__main__.py
```

O arquivo será criado em `dist\DanteSquash.exe`. Cada atualização do código
exige gerar e distribuir um novo executável.

## Testes

Os testes de caracterização começaram antes da implementação das regras do
domínio e foram executados sem depender da interface gráfica ou de uma instância
PostgreSQL:

```powershell
py -m unittest discover -s tests -v
```

Cobrem validações de preço e reserva, mensalidades/aulas, faixas de multa,
pagamento parcial/desconto, consumo, sauna, compatibilidade de datas e limites
de dependência entre camadas. Testes de integração PostgreSQL continuam
necessários para validar o DDL e as consultas contra uma instância real do
MariaDB e do PostgreSQL.

## Cenários BDD (item 3)

Os testes de aceitação foram escritos em BDD (Behavior-Driven Development).
Os cenários estão em Gherkin português (`Dado`/`Quando`/`Então`) e são
executados com [behave](https://behave.readthedocs.io/). Eles passam pela camada
de serviços real da aplicação, a mesma usada pela interface Tkinter. O banco é
substituído por uma unidade de trabalho em memória que implementa as portas de
`dante_squash/ports.py`. Por isso os cenários não precisam de MariaDB nem de
PostgreSQL e rodam em menos de um segundo.

### Estrutura

| Caminho | Conteúdo |
|---|---|
| `behave.ini` | configuração do behave (pasta `features`, idioma `pt`) |
| `requirements-bdd.txt` | dependências para rodar o BDD (`requirements.txt` + behave) |
| `features/*.feature` | 9 funcionalidades e 68 cenários |
| `features/steps/` | implementação dos passos: cadastros, squash, financeiro e comuns |
| `features/support/` | banco em memória, tipos de parâmetro (dinheiro, data, dia da semana) e utilitários |
| `features/environment.py` | cria um banco vazio e os serviços antes de cada cenário |
| `reports/` | relatório texto e JUnit XML da última execução |
| `docs/BDD.md` | metodologia, ligação cenário × requisito e análise dos resultados |

### Funcionalidades cobertas

| Funcionalidade | Cenários |
|---|---|
| 01 Cadastro de clientes | 6 |
| 02 Cadastro de produtos | 7 |
| 03 Tabela de valores | 9 |
| 04 Reservas de squash | 11 |
| 05 Mensalidades | 5 |
| 06 Multas | 7 |
| 07 Consumo de produtos | 7 |
| 08 Pagamentos | 6 |
| 09 Sauna | 10 |
| **Total** | **68** |

Cada funcionalidade tem uma tag de requisito (por exemplo `@multas`) e cada
regra de negócio tem uma tag `@regra_...`. Comportamentos legados preservados
de propósito usam `@defeito_D0x`.

### Como executar

Na pasta raiz do projeto, no PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-bdd.txt
.\.venv\Scripts\python.exe -m behave
```

Para rodar só um requisito ou uma regra:

```powershell
.\.venv\Scripts\python.exe -m behave --tags=@multas
.\.venv\Scripts\python.exe -m behave --tags=@regra_pagamento_parcial
```

Para gerar novamente os relatórios da pasta `reports/`:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m behave --no-color -f pretty -o reports/bdd_resultado.txt --junit --junit-directory reports/junit
```

### Resultados

Execução em 26/11/2026, com behave 1.3.3:

| | Passaram | Falharam |
|---|---|---|
| Funcionalidades | 8 | 1 |
| Cenários | 67 | 1 |
| Passos | 317 | 1 |

O único cenário que falha, **"Cadastrar um produto válido"**
(`features/02_cadastro_produtos.feature:12`, tag `@defeito_encontrado`),
mostra um defeito real da versão Python que o BDD encontrou. A tela de produtos
envia o código 0 para um produto novo, e `Product.validate()` recusa esse código
("Os códigos 0 e 1 são de uso interno da aplicação!") antes de
`CatalogService.save_product` gerar o próximo código. Na prática, não é possível
cadastrar um produto novo pela interface. Os testes unitários não pegaram o
problema porque não exercitam esse fluxo. O cenário fica verde assim que o
defeito for corrigido, sem alterar o BDD.

Sem esse cenário, todas as funcionalidades passam:

```powershell
.\.venv\Scripts\python.exe -m behave --tags="not @defeito_encontrado"
# 9 features passed, 0 failed — 67 scenarios passed, 1 skipped
```

O cenário `@defeito_D01` confirma que o comportamento legado D01 (a primeira
multa impede a segunda no mesmo mês) foi preservado. Os detalhes estão em
`docs/BDD.md`.

## Arquivos para versionar

Para executar a versão Python, versione `dante_squash/`, `requirements.txt`,
`README.md` e `.gitignore`. Inclua também `tests/` para manter os testes,
`features/`, `behave.ini`, `requirements-bdd.txt`, `docs/` e `reports/` para os
cenários BDD, e `requirements-build.txt` se o grupo for gerar executáveis. `src/` contém o
programa Java legado e não é necessário para iniciar a aplicação Python; pode
ser mantido no repositório se o grupo quiser preservar a implementação antiga.
Não versione `.venv/`, `build/`, `dist/`, arquivos `.spec` gerados localmente,
senhas/DSNs nem o JDK que possa estar dentro da pasta de legado Java.

## Prompt original

```text
Atue como engenheiro de software

 - Preciso que realize uma refatoração deste código para a linguagem de programação python.
 - Para isso quero que siga as boas praticas de programação aplicando os principios de programação orientada a objetos.
 - Também aplique melhorias de arquitetura encontradas no pdf anexado.

  Obs: As regras de negocio tem que manter as mesmas, então se possível antes de implementar crie testes TDD antes de refatorar para vermos se depois da refatoração os resultados são os mesmos.

  No final gere um readme.md com um relatorio desta refatoração incluindo esse prompt que lhe foi enviado.
```
