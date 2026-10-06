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

## Dados

Os dados brutos utilizados no projeto correspondem aos registros de viagens a serviço dos Institutos Federais da região Nordeste selecionados para a análise, referentes aos anos de 2024 e 2025.

Como os arquivos brutos possuem tempo elevado para serem carregados, sugere-se usar os dados já baixados. A base completa pode ser obtida no seguinte endereço:

[Baixar dados brutos (2024–2025)](https://drive.google.com/drive/folders/1FOlScIaF38t1rK5bPHRZ3EAngkWjmBl6?usp=sharing)

Após o download, extraia os arquivos para:

data/raw/

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

### data/trusted/

O `transform.py` grava `data/trusted/viagens.parquet`, com os dados limpos e validados por um contrato (Pandera). Na coleta de 30/09/2026 foram 47.357 viagens.

Colunas criadas no tratamento (indicam o que foi preenchido pela equipe, e não medido pela fonte):

| Coluna | Significado |
| ------ | ----------- |
| `cargo_imputado` | `cargo.descricao` estava vazio e foi preenchido com "Não informado" |
| `descricaoPoder_imputada`, `cnpj_imputada`, `sigla_imputada`, `nome_imputada` | O bloco `unidadeGestoraResponsavel.*` estava vazio e foi preenchido pela moda |

> **Atenção:** quando uma das flags `_imputada` do bloco da unidade gestora é verdadeira, os campos `unidadeGestoraResponsavel.orgaoVinculado.cnpj`, `.sigla` e `.nome` **não são confiáveis**: a moda atribui o mesmo instituto a todas essas linhas, e na maior parte delas o valor está errado. Para saber a que instituto a viagem pertence, use `orgao.sigla`, que é sempre preenchida. Filtre pelas flags antes de usar esses campos.

Outras decisões do tratamento: a coluna `beneficiario.nis`, vazia em 100% dos registros, foi descartada. Em 3 viagens da unidade "Sigilosa", `beneficiario.cpfFormatado` e `cargo.codigoSIAPE` estão ausentes, e o contrato aceita isso apenas nessa unidade.

### data/quarentena/

O `transform.py` grava `data/quarentena/rejeitados.parquet` com as viagens que violam alguma regra do contrato, junto com a coluna `motivo` e a data de detecção (`detectado_em`). As linhas não são descartadas e podem ser reprocessadas. Na coleta de 30/09/2026 foram 2 viagens, ambas pelo motivo `devolucao_maior_que_viagem`.

Ao final da execução, o script imprime a quantidade de linhas em cada pasta e o resumo por motivo.
