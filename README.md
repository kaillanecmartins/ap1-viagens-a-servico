# Análise de viagens a serviço dos Institutos Federais do Nordeste

Projeto da disciplina de Introdução à Ciência de Dados para coleta e análise de viagens a serviço dos Institutos Federais de Educação, Ciência e Tecnologia do Nordeste.

Os dados são obtidos da **API de Dados do Portal da Transparência do Governo Federal**, utilizando o endpoint `/viagens`. A coleta considera os anos de **2024 e 2025**, em períodos mensais, para os 11 Institutos Federais selecionados.

## Chave da API

A API utiliza uma chave de acesso. caso ainda não possua uma chave de api do portal da transparência, é necessário se cadastrar em: [Cadastrar E-mail](https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email)

Depois de obter a chave, crie o arquivo `.env` a partir do `.env.example` e informe:

```env
API_KEY=sua_chave_api
```

A chave não deve ser adicionada ao código-fonte nem versionada no Git.

## Variáveis de ambiente

As configurações da coleta são armazenadas no arquivo `.env`. O projeto utiliza as seguintes variáveis:

| Variável            | Descrição                                              |
| ------------------- | ------------------------------------------------------ |
| `API_BASE_URL`      | URL base da API                                        |
| `API_ENDPOINT`      | Endpoint utilizado na coleta                           |
| `API_KEY`           | Chave de acesso à API                                  |
| `ORGAOS_FILE`       | Arquivo com os órgãos selecionados                     |
| `ORGAOS_CODIGO_COL` | Coluna que contém o código do órgão                    |
| `ORGAOS_NOME_COL`   | Coluna que contém o nome do órgão                      |
| `DATA_INICIO`       | Data inicial da coleta                                 |
| `DATA_FIM`          | Data final da coleta                                   |
| `MESES_POR_COLETA`  | Quantidade de meses consultados por requisição         |
| `PAGE_SIZE`         | Quantidade de registros solicitados por página         |
| `REQUEST_TIMEOUT`   | Tempo limite das requisições                           |
| `MAX_TENTATIVAS`    | Número máximo de tentativas para erros recuperáveis    |
| `BACKOFF_BASE`      | Base utilizada para o tempo de espera entre tentativas |
| `RAW_DIR`           | Diretório onde os dados brutos serão armazenados       |

Exemplo de configuração:

```env
API_BASE_URL=https://api.portaldatransparencia.gov.br/api-de-dados
API_ENDPOINT=/viagens
API_KEY=sua_chave_api

ORGAOS_FILE=config/ifs_nordeste.csv
ORGAOS_CODIGO_COL=codigo
ORGAOS_NOME_COL=nome

DATA_INICIO=01/01/2024
DATA_FIM=31/12/2025
MESES_POR_COLETA=1

PAGE_SIZE=100
REQUEST_TIMEOUT=30
MAX_TENTATIVAS=5
BACKOFF_BASE=2

RAW_DIR=data/raw/portal_transparencia
```

O arquivo `.env` contém informações de configuração e credenciais e, por isso, não deve ser versionado no Git.

## Execução

Instale as dependências:

```bash
uv sync
```

Execute a coleta dos dados:

```bash
uv run python src/ingest.py
```

Gere o diagnóstico dos dados coletados:

```bash
uv run quarto render diagnostico.qmd
```

Execute a transformação dos dados:

```bash
uv run python src/transform.py
```

A sequência completa é:

```bash
uv sync
uv run python src/ingest.py
uv run quarto render diagnostico.qmd
uv run python src/transform.py
```

A coleta é idempotente: se um órgão e período já tiverem sido coletados, uma nova execução não realiza novamente aquela coleta.

## Resultados

Após a execução, os dados brutos ficam em:

```text
data/raw/portal_transparencia/
```

organizados por órgão, ano e mês, com a data da coleta registrada no nome do arquivo:

```text
data/raw/portal_transparencia/
└── <codigo_orgao>/
    └── <ano>/
        └── <mes>/
            └── viagens_<data_da_coleta>.json
```

A camada `data/trusted/` contém os dados tratados e preparados para análise pelo `transform.py`.

A pasta `data/quarentena/` contém os registros que não atendem às regras definidas para a camada trusted durante o tratamento dos dados.

Ao finalizar a coleta, o programa informa a quantidade de registros coletados e o diretório onde os dados foram gravados.
