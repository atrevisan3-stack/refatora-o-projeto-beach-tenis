# Item 3 — Implementação dos Cenários BDD

## 1. Ferramentas e abordagem

| Item | Escolha |
|---|---|
| Linguagem dos cenários | Gherkin em português (`# language: pt`): `Funcionalidade`, `Contexto`, `Cenário`, `Esquema do Cenário`, `Exemplos`, `Dado`, `Quando`, `Então`, `E` |
| Framework de execução | [behave](https://behave.readthedocs.io/) 1.3 (BDD para Python) |
| Relatórios | saída `pretty` em texto e JUnit XML, que IDEs e pipelines de integração contínua conseguem ler |
| Apoio de IA | Claude Code, para derivar os cenários das regras do código, escrever os passos e analisar as falhas |

Os cenários passam pela **camada de serviços real** da aplicação: `CatalogService`, `ConsumptionService`, `PaymentService`, `MonthlyBillingService` e `SaunaService`. Também usam as entidades do domínio. O mesmo caminho é usado pela interface Tkinter.

O banco é trocado por uma **unidade de trabalho em memória** em [features/support/memoria.py](../features/support/memoria.py). Ela implementa as mesmas portas de `dante_squash/ports.py` que os adaptadores PostgreSQL e MariaDB. Também reproduz a semântica das consultas legadas:

- o mês é lido da data gravada como DDMMAAAA, com base zero;
- a conta da sauna está fechada quando todos os lançamentos estão pagos;
- a diferença do fechamento da sauna é lançada na entrada;
- o estado é restaurado quando um caso de uso falha, como em um rollback.

Assim os cenários rodam em menos de um segundo e não dependem de servidor de banco de dados. Cada cenário começa com um banco vazio, criado pelo gancho `before_scenario` em [features/environment.py](../features/environment.py).

## 2. Estrutura

```text
behave.ini                       configuração (pasta features, idioma pt)
requirements-bdd.txt             dependências para rodar o BDD
features/
  01_cadastro_clientes.feature   ... 09_sauna.feature   cenários Gherkin
  environment.py                 monta os serviços com o banco em memória por cenário
  steps/
    comuns_steps.py              Dado de preparação, aceite e recusa com mensagem
    cadastros_steps.py           clientes, produtos e tabela de valores
    squash_steps.py              reservas, mensalidades e multas
    financeiro_steps.py          consumo, pagamentos e sauna
  support/
    memoria.py                   adaptador em memória das portas do sistema
    tipos.py                     tipos de parâmetro: dinheiro "5,00", data "12/03/2026", dia da semana
    ajuda.py                     captura de BusinessRuleError e comparação de valores
reports/                         resultados da última execução
```

## 3. Ligação entre cenários e requisitos

Cada funcionalidade tem uma tag de requisito, por exemplo `@cadastro_clientes`. Cada regra de negócio tem uma tag `@regra_...`. Os comportamentos legados mantidos de propósito usam `@defeito_D0x`. A coluna **RF da Entrega 1** deve ser preenchida pelo grupo com a numeração do documento da Entrega 1.

| Arquivo | Tag do requisito | RF da Entrega 1 | Regras de negócio verificadas | Cenários |
|---|---|---|---|---|
| 01_cadastro_clientes | `@cadastro_clientes` | RF__ | código gerado automaticamente; edição mantém o código; nome obrigatório; nome com até 50 caracteres; CPF com até 11 caracteres | 6 |
| 02_cadastro_produtos | `@cadastro_produtos` | RF__ | descrição, preço maior que zero e unidade obrigatórios; códigos 0 e 1 reservados | 7 |
| 03_tabela_valores | `@tabela_valores` | RF__ | sauna e aula maiores que zero; de 1 a 3 faixas; dias entre 1 e 28 e diferentes; dia e valor informados juntos; valor maior que zero | 9 |
| 04_reservas_squash | `@reservas_squash` | RF__ | segunda a sábado; quadras 1 a 3; horários da grade; aula com um único cliente; cliente cadastrado e sem repetição; substituição só com confirmação | 11 |
| 05_mensalidades | `@mensalidades` | RF__ | jogo rateado pelo valor da 1ª faixa; aula vale 4 aulas; geração idempotente no mês; exige tabela de valores | 5 |
| 06_multas | `@multas` | RF__ | 1ª multa entre o 2º e o 3º vencimento; 2ª multa a partir do 3º; fora do período é recusada; multa única no mês; quem pagou não é multado; aula não é multada; defeito D01 | 7 |
| 07_consumo_produtos | `@consumo_produtos` | RF__ | cliente informado e cadastrado; quantidade maior que zero; produto cadastrado e não interno; sequência por dia | 7 |
| 08_pagamentos | `@pagamentos` | RF__ | pagamento total; parcial com saldo em aberto; desconto lançado como crédito quitado; valor e cliente obrigatórios; nada é gravado quando recusado | 6 |
| 09_sauna | `@sauna` | RF__ | entrada cobra o valor da sauna; nome único no dia sem diferenciar maiúsculas; consumo soma na conta; fechamento quita e ajusta a diferença; conta fechada não aceita consumo; só o dia de hoje | 10 |
| **Total** | | | | **68** |

Para rodar apenas um requisito ou uma regra, use as tags:

```powershell
.\.venv\Scripts\python.exe -m behave --tags=@multas
.\.venv\Scripts\python.exe -m behave --tags=@regra_pagamento_parcial
```

## 4. Como executar

Na pasta raiz do projeto, no PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-bdd.txt
.\.venv\Scripts\python.exe -m behave
```

Para gerar os relatórios da pasta `reports/`:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m behave --no-color -f pretty -o reports/bdd_resultado.txt --junit --junit-directory reports/junit
```

## 5. Resultados da execução

Execução em 25/11/2026, com Python 3.12.10 e behave 1.3.3:

| | Passaram | Falharam |
|---|---|---|
| Funcionalidades | 8 | 1 |
| Cenários | 67 | 1 |
| Passos | 317 | 1 |

O relatório completo, passo a passo, está em [reports/bdd_resultado.txt](../reports/bdd_resultado.txt). Os arquivos JUnit estão em `reports/junit/`.

### Defeito encontrado pelo BDD

O cenário **"Cadastrar um produto válido"** falha, e a falha é um defeito real da versão Python.

```text
Quando eu cadastro o produto "Água mineral" com preço 5,00 e unidade "un"
Então o produto "Água mineral" deve estar cadastrado com código 2 e preço 5,00
  ASSERT FAILED: O cadastro foi recusado: Os códigos 0 e 1 são de uso interno da aplicação!
```

- **Causa:** a tela de produtos envia o código 0 para um produto novo, como faz para clientes. `Product.validate()` recusa o código 0 antes de `CatalogService.save_product` gerar o próximo código.
- **Impacto:** pela interface, não é possível cadastrar nenhum produto novo. Os testes unitários não pegaram o problema porque não exercitam o fluxo "novo produto com código 0".
- **Encaminhamento:** a correção é da reconstrução e dos testes, nos itens 1 e 2. Uma opção é validar os códigos reservados só quando o código vier preenchido, ou validar depois de gerar o código. O cenário tem a tag `@defeito_encontrado` e passa a ficar verde assim que a correção for feita, sem alterar o BDD.

Sem esse cenário, todos os demais passam:

```text
.\.venv\Scripts\python.exe -m behave --tags="not @defeito_encontrado"
9 features passed, 0 failed, 0 skipped
67 scenarios passed, 0 failed, 1 skipped
```

### Comportamentos legados verificados

- **D01:** a primeira multa do mês impede a segunda. O cenário com a tag `@defeito_D01` confirma que esse comportamento foi preservado, como pede o relatório da Entrega 1.
- **D02:** as datas de dias 1 a 9 são lidas como sete dígitos, o que gera mês e ano errados. Os cenários de multa usam dias a partir de 10 para não depender desse defeito. Ele continua coberto pelos testes de caracterização do item 2.
