# Dante Squash & Sauna — reconstrução em Python (Entrega 2)

Sistema desktop para clube com sauna, três quadras de squash e venda de produtos,
reconstruído em Python a partir dos requisitos (RF01–RF18) e regras de negócio
(RN01–RN30) levantados na Entrega 1.

- **Linguagem:** Python 3.10 ou superior
- **Interface:** Tkinter (já vem com o Python no Windows)
- **Banco de dados:** PostgreSQL 16 (recomendado rodar no Docker)
- **Testes:** pytest, pytest-cov e Testcontainers

## 1. Arquitetura

```
dante_squash/
├── domain.py            Entidades e regras puras (sem banco, sem interface)
├── ports.py             Interfaces dos repositórios, relógio e exportação
├── services/            Casos de uso (cadastros, sauna, squash, pagamentos, relatórios, backup)
├── infrastructure/      PostgreSQL (repositórios, esquema, backup CSV) e relógio do sistema
├── presentation/        Telas Tkinter; só chamam serviços
├── composition.py       Cria e conecta todos os objetos (injeção de dependências)
└── __main__.py          Ponto de entrada: python -m dante_squash
```

O sentido das dependências é `presentation → services → ports/domain`, e
`infrastructure → ports/domain`. Os testes de arquitetura verificam isso
automaticamente.

**Nada estático.** Não há `@staticmethod`, `@classmethod`, funções soltas nem
variáveis de módulo ou de classe no código do sistema. Constantes de negócio
(códigos internos de produto, horários do squash, arredondamento de dinheiro)
ficam em objetos criados na composição e injetados. Os testes de arquitetura
também verificam essa regra.

## 2. Mudanças em relação à versão anterior do grupo

| Item | Antes | Agora |
| --- | --- | --- |
| Banco | MariaDB (padrão) + PostgreSQL | Só PostgreSQL, como na Entrega 1 |
| Datas e valores no banco | `INTEGER` DDMMAAAA e `DOUBLE PRECISION` | `DATE` e `NUMERIC(10,2)` |
| Métodos estáticos | 10 `@staticmethod`/`@classmethod` e funções soltas | Nenhum |
| Defeito D01 (2ª multa) | Bloqueada se a 1ª existisse | Corrigido: cada multa uma vez por mês |
| Defeito D02 (datas dias 1–9) | Mês lido errado | Corrigido com `DATE` |
| Defeito D03 (dia 31 no resumo) | Ficava fora | Corrigido: todos os dias do mês |
| Defeito D04 (ponto flutuante) | Comparação de `double` | Corrigido com `Decimal` |
| Defeito D05 (pagamento `NaN`) | Aceito | Corrigido: rejeitado |
| Mensalidade de aula (antigo D08) | Sempre × 4 | Número real de aulas no mês |
| Produto novo | Recebia código 0 e era rejeitado | Código gerado automaticamente (a partir de 2) |
| Exclusão de cliente com reserva | Não verificada | Bloqueada com mensagem clara |
| Funcionalidades | Faltavam RF10, RF13–RF16 e exclusões | Todas implementadas |

## 3. Funcionalidades (abas da janela)

| Aba | Requisito |
| --- | --- |
| Sauna | RF06, RF07, RF08 |
| Grade do squash | RF10 |
| Reservas de squash | RF09 |
| Mensalidades e multas | RF11, RF12 |
| Clientes | RF01 |
| Produtos | RF02 |
| Valores | RF03 |
| Consumos | RF04 |
| Pagamentos | RF05 |
| Ficha do cliente | RF13 |
| Fluxo de caixa | RF14 |
| Resumo mensal | RF15 |
| Backup | RF16 |

As tabelas e a carga padrão são criadas automaticamente ao iniciar (RF17, RF18).

## 4. Instalação (Windows, PowerShell)

Pré-requisitos: Python 3.10+, Docker Desktop aberto e Git (ou o .zip do projeto).

Na pasta do projeto (onde está este README):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 5. Executar o sistema

### 5.1 Subir o PostgreSQL no Docker (uma vez)

```powershell
docker run --name dante-postgres -e POSTGRES_USER=dante -e POSTGRES_PASSWORD=dante `
  -e POSTGRES_DB=dante_squash -p 5432:5432 -d postgres:16-alpine
```

Nas próximas vezes basta `docker start dante-postgres`. Essa senha simples serve
só para o banco local de desenvolvimento.

### 5.2 Iniciar a aplicação

```powershell
$env:DANTE_SQUASH_DSN = "postgresql://dante:dante@localhost:5432/dante_squash"
.\.venv\Scripts\python.exe -m dante_squash
```

Na primeira execução, configure a aba **Valores** antes de usar Sauna e Squash.

## 6. Testes automatizados

Com o Docker Desktop aberto:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Os testes de banco sobem sozinhos um PostgreSQL descartável no Docker
(Testcontainers) e não tocam no banco `dante_squash`. Sem Docker, eles são
pulados com aviso. Para usar um PostgreSQL já existente, defina
`DANTE_SQUASH_TEST_DSN` (o banco indicado é apagado e recriado a cada teste).

### Por tipo

```powershell
.\.venv\Scripts\python.exe -m pytest tests/flow           # fluxo principal
.\.venv\Scripts\python.exe -m pytest tests/database       # banco de dados
.\.venv\Scripts\python.exe -m pytest tests/architecture   # arquitetura
.\.venv\Scripts\python.exe -m pytest tests/gui            # interface gráfica
.\.venv\Scripts\python.exe -m pytest tests/unit tests/business   # regras de negócio
```

### Evidências (cobertura e relatório)

```powershell
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=html --cov-report=term `
  --junitxml=relatorios/resultado-testes.xml
```

Abra `htmlcov/index.html` para a cobertura e use `relatorios/resultado-testes.xml`
como evidência da execução.

### Organização e rastreabilidade

| Pasta | Tipo | Casos da Entrega 1 |
| --- | --- | --- |
| `tests/unit` | Unidade (domínio puro) | CT03, regras de RN01, RN03, RN05, RN06, RN14, RN19, D04, D05, D08 |
| `tests/business` | Regras pelos serviços, em memória **e** no PostgreSQL | CT04–CT12, CT14, CT17 |
| `tests/flow` | Fluxo principal, de ponta a ponta | CT01, CT02 |
| `tests/database` | Banco de dados real | CT13, CT15, CT16, backup |
| `tests/architecture` | Arquitetura e "nada estático" | CT18, CT19, CT20 |
| `tests/gui` | Interface gráfica (Tkinter real) | CT21–CT25 |

Os testes de `tests/business` e `tests/flow` rodam duas vezes: no banco em
memória (`tests/support/fakes.py`) e no PostgreSQL.

### Cenários BDD (behave)

Os testes de aceitação estão em BDD, com cenários em Gherkin português
(`Dado`/`Quando`/`Então`) executados pelo [behave](https://behave.readthedocs.io/).
Eles usam os serviços reais, montados pelo `ServiceFactory`, sobre o banco em
memória de `tests/support/fakes.py`. Não precisam de Docker e rodam em menos de
um segundo.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-bdd.txt
.\.venv\Scripts\python.exe -m behave
.\.venv\Scripts\python.exe -m behave --tags=@multas      # um requisito
```

| Caminho | Conteúdo |
| --- | --- |
| `features/*.feature` | 12 funcionalidades e 102 cenários |
| `features/steps/` | implementação dos passos |
| `features/support/` | tipos de parâmetro (dinheiro, data, dia da semana) e utilitários |
| `features/environment.py` | monta os serviços sobre um banco novo antes de cada cenário |
| `reports/` | relatório texto e JUnit XML da última execução |
| `docs/BDD.md` | metodologia, ligação cenário × requisito e análise dos resultados |

Última execução (26/11/2026, behave 1.3.3): 12 funcionalidades, 102 cenários e
586 passos, todos aprovados. Além dos cadastros, squash, pagamentos e sauna,
os cenários cobrem exclusões, relatórios (ficha, caixa, resumo mensal e grade)
e backup. O BDD encontrou um defeito real (não era possível
cadastrar um produto novo pela interface), que já foi corrigido. Os cenários
também verificam as correções de D01 e da mensalidade de aula. Os detalhes
estão em `docs/BDD.md`.

Para gerar novamente os relatórios:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -m behave --no-color -f pretty -o reports/bdd_resultado.txt --junit --junit-directory reports/junit
```

## 7. Gerar executável (opcional)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onefile `
  --name DanteSquash dante_squash\__main__.py
```

O executável fica em `dist\DanteSquash.exe` e continua precisando de
`DANTE_SQUASH_DSN` e de um PostgreSQL acessível.

## 8. Limitações conhecidas

- Os dados do *dump* original (`base_dados_squash.sql`) não são migrados
  automaticamente: o esquema novo usa `DATE` e `NUMERIC`. Além disso, o dump
  contém dados pessoais reais e não deve ser usado como massa de teste (LGPD).
- A restauração de backup não foi implementada: no sistema original ela também
  não tinha opção no menu.
- "Excluir esquema" (menu oculto no original) existe apenas para os testes
  (`PostgresDatabase.drop_all`), não na interface.
- A pasta `src/` contém o código Java original, mantido só como referência.

## Prompt original

```text
Atue como engenheiro de software

 - Preciso que realize uma refatoração deste código para a linguagem de programação python.
 - Para isso quero que siga as boas praticas de programação aplicando os principios de programação orientada a objetos.
 - Também aplique melhorias de arquitetura encontradas no pdf anexado.

  Obs: As regras de negocio tem que manter as mesmas, então se possível antes de implementar crie testes TDD antes de refatorar para vermos se depois da refatoração os resultados são os mesmos.

  No final gere um readme.md com um relatorio desta refatoração incluindo esse prompt que lhe foi enviado.
```
