# Item 3 — Implementação dos Cenários BDD

## 1. Ferramentas e abordagem

| Item | Escolha |
|---|---|
| Linguagem dos cenários | Gherkin em português (`# language: pt`): `Funcionalidade`, `Contexto`, `Cenário`, `Esquema do Cenário`, `Exemplos`, `Dado`, `Quando`, `Então`, `E` |
| Framework de execução | [behave](https://behave.readthedocs.io/) 1.3 (BDD para Python) |
| Relatórios | saída `pretty` em texto e JUnit XML, que IDEs e pipelines de integração contínua conseguem ler |
| Apoio de IA | Claude Code, para derivar os cenários das regras do código, escrever os passos e analisar as falhas |

Os cenários passam pela **camada de serviços real** da aplicação: `CatalogService`, `ReservationService`, `ConsumptionService`, `PaymentService`, `MonthlyBillingService`, `SaunaService`, `ReportService` e `BackupService`. Os serviços são montados pela mesma raiz de composição da aplicação (`ServiceFactory` em `dante_squash/composition.py`), que também atende a interface Tkinter.

O banco é trocado pela **unidade de trabalho em memória** dos testes pytest, em [tests/support/fakes.py](../tests/support/fakes.py). Ela implementa as mesmas portas de `dante_squash/ports.py` que o adaptador PostgreSQL e desfaz as alterações quando um caso de uso falha, como um rollback. A data de hoje vem de um relógio fixo (`FixedClock`), que o passo `Dado que hoje é "..."` altera.

Assim os cenários rodam em menos de um segundo e não dependem de servidor de banco de dados. Cada cenário começa com um banco novo, só com os registros internos (cliente 0 e produtos 0, 1, −1, −2 e −3), criado pelo gancho `before_scenario` em [features/environment.py](../features/environment.py).

## 2. Estrutura

```text
behave.ini                       configuração (pasta features, idioma pt)
requirements-bdd.txt             dependências para rodar o BDD
features/
  01_cadastro_clientes.feature   ... 12_backup.feature  cenários Gherkin
  environment.py                 monta os serviços (ServiceFactory) sobre o banco em memória por cenário
  steps/
    comuns_steps.py              Dado de preparação, aceite e recusa com mensagem
    cadastros_steps.py           clientes, produtos e tabela de valores
    squash_steps.py              reservas, mensalidades e multas
    financeiro_steps.py          consumo, pagamentos e sauna
    exclusoes_steps.py           exclusão de clientes, produtos, consumos, reservas e sauna
    relatorios_steps.py          ficha do cliente, fluxo de caixa, resumo mensal, grade e backup
  support/
    tipos.py                     tipos de parâmetro: dinheiro "5,00", data "12/03/2026", dia da semana
    ajuda.py                     captura de BusinessRuleError e comparação de valores
reports/                         resultados da última execução
```

## 3. Ligação entre cenários e requisitos

Cada funcionalidade tem uma tag de requisito, por exemplo `@cadastro_clientes`. Cada regra de negócio tem uma tag `@regra_...`. Os defeitos do sistema original usam `@defeito_D0x`, e os já corrigidos têm também `@defeito_corrigido`. A coluna **RF da Entrega 1** deve ser preenchida pelo grupo com a numeração do documento da Entrega 1.

| Arquivo | Tag do requisito | RF da Entrega 1 | Regras de negócio verificadas | Cenários |
|---|---|---|---|---|
| 01_cadastro_clientes | `@cadastro_clientes` | RF__ | código gerado automaticamente; edição mantém o código; nome obrigatório; nome com até 50 caracteres; CPF com até 11 caracteres | 6 |
| 02_cadastro_produtos | `@cadastro_produtos` | RF__ | descrição, preço maior que zero e unidade obrigatórios; códigos 0 e 1 reservados | 7 |
| 03_tabela_valores | `@tabela_valores` | RF__ | sauna e aula maiores que zero; de 1 a 3 faixas; dias entre 1 e 28 e diferentes; dia e valor informados juntos; valor maior que zero | 9 |
| 04_reservas_squash | `@reservas_squash` | RF__ | segunda a sábado; quadras 1 a 3; horários da grade; aula com um único cliente; cliente cadastrado e sem repetição; substituição só com confirmação | 11 |
| 05_mensalidades | `@mensalidades` | RF__ | jogo rateado pelo valor da 1ª faixa; aula vale o número de aulas do mês; geração idempotente no mês; exige tabela de valores | 5 |
| 06_multas | `@multas` | RF__ | 1ª multa entre o 2º e o 3º vencimento; 2ª multa a partir do 3º; fora do período é recusada; multa única no mês; quem pagou não é multado; aula não é multada; D01 corrigido (a 1ª multa não impede a 2ª) | 7 |
| 07_consumo_produtos | `@consumo_produtos` | RF__ | cliente informado e cadastrado; quantidade maior que zero; produto cadastrado e não interno; sequência por dia | 7 |
| 08_pagamentos | `@pagamentos` | RF__ | pagamento total; parcial com saldo em aberto; desconto lançado como crédito quitado; valor e cliente obrigatórios; nada é gravado quando recusado | 6 |
| 09_sauna | `@sauna` | RF__ | entrada cobra o valor da sauna; nome único no dia sem diferenciar maiúsculas; consumo soma na conta; fechamento quita e ajusta a diferença; conta fechada não aceita consumo; só o dia de hoje | 10 |
| 10_exclusoes | `@exclusoes` | RF__ | cliente sem movimentação pode ser excluído, com consumo ou reserva não; produto nunca consumido pode ser excluído, consumido ou interno não; consumo pago não pode ser excluído; reserva excluída libera o horário; frequentador e consumo da sauna removidos só com a conta aberta; a entrada da sauna não pode ser excluída | 20 |
| 11_relatorios | `@relatorios` | RF13, RF14, RF15, RF10 | ficha com reservas, histórico e total em aberto; caixa separado em sauna, squash e produtos, sem o saldo; sauna pelo valor pago; resumo com todos os dias do mês, inclusive o 31 (D03 corrigido); grade do dia com aulas marcadas | 11 |
| 12_backup | `@backup` | RF16 | arquivos com data e hora da exportação; pasta inexistente recusada | 3 |
| **Total** | | | | **102** |

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

Execução em 26/11/2026, com Python 3.15.0 e behave 1.3.3:

| | Passaram | Falharam |
|---|---|---|
| Funcionalidades | 12 | 0 |
| Cenários | 102 | 0 |
| Passos | 586 | 0 |

O relatório completo, passo a passo, está em [reports/bdd_resultado.txt](../reports/bdd_resultado.txt). O resumo está em [reports/bdd_resumo.txt](../reports/bdd_resumo.txt) e os arquivos JUnit em `reports/junit/`.

### Defeito encontrado pelo BDD (corrigido)

Na primeira execução, o cenário **"Cadastrar um produto válido"** falhava com um defeito real da versão Python:

```text
Quando eu cadastro o produto "Água mineral" com preço 5,00 e unidade "un"
Então o produto "Água mineral" deve estar cadastrado com código 2 e preço 5,00
  ASSERT FAILED: O cadastro foi recusado: Os códigos 0 e 1 são de uso interno da aplicação!
```

- **Causa:** a tela de produtos enviava o código 0 para um produto novo, e `Product.validate()` recusava esse código antes de `CatalogService.save_product` gerar o próximo.
- **Impacto:** pela interface, não era possível cadastrar nenhum produto novo.
- **Correção:** um registro novo agora vai com código `None` e o serviço gera o próximo código. O cenário, com a tag `@defeito_corrigido`, passou sem mudar o que ele verifica.

### Ajustes depois da correção dos itens 1 e 2

A correção dos itens 1 e 2 mudou algumas regras e mensagens, e os cenários foram atualizados para elas:

- **D01 corrigido:** a primeira multa do mês não impede mais a segunda. O cenário `@defeito_D01` agora verifica que, depois da 1ª multa no dia 22, a geração no dia 26 lança a 2ª multa.
- **Mensalidade de aula (RN23):** vale o valor da aula vezes o número de aulas do mês, e não mais 4 aulas fixas. Março/2026 tem 5 terças-feiras, então a mensalidade da aula é 5 × 50,00 = 250,00.
- **D02 corrigido:** as datas passaram a ser gravadas como `DATE`, então o mês é lido corretamente em qualquer dia.
- **Mensagens:** as mensagens de validação de reservas, tabela de valores, CPF, consumo e sauna seguem agora o texto do sistema original e os cenários usam esse texto.
