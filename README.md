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

| Variável                | Descrição                                                          |
| ----------------------- | ------------------------------------------------------------------ |
| `API_BASE_URL`          | URL base da API                                                    |
| `API_ENDPOINT`          | Endpoint utilizado na coleta                                       |
| `API_KEY`               | Chave de acesso à API                                              |
| `ORGAOS_FILE`           | Arquivo com os órgãos selecionados                                 |
| `ORGAOS_CODIGO_COL`     | Coluna que contém o código do órgão                                |
| `ORGAOS_NOME_COL`       | Coluna que contém o nome do órgão                                  |
| `DATA_INICIO`           | Data inicial da coleta                                             |
| `DATA_FIM`              | Data final da coleta                                               |
| `MESES_POR_COLETA`      | Quantidade de meses consultados por requisição                     |
| `PAGE_SIZE`             | Quantidade de registros solicitados por página                     |
| `REQUEST_TIMEOUT`       | Tempo limite das requisições                                       |
| `MAX_TENTATIVAS`        | Número máximo de tentativas para erros recuperáveis                |
| `BACKOFF_BASE`          | Base utilizada para o tempo de espera entre tentativas             |
| `INTERVALO_REQUISICOES` | Intervalo mínimo entre o início das requisições à API, em segundos |
| `RAW_DIR`               | Diretório onde os dados brutos serão armazenados                   |

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
INTERVALO_REQUISICOES=0.7

RAW_DIR=data/raw/portal_transparencia
```

O arquivo `.env` contém informações de configuração e credenciais e, por isso, não deve ser versionado no Git.

## Execução

### 1. Obter o projeto

Clone o repositório:

```bash
git clone <url-do-repositorio>
```

Acesse a pasta do projeto:

```bash
cd ap1-viagens-a-servico
```

### 2. Configurar o ambiente

Crie o arquivo `.env` a partir do modelo disponibilizado:

```bash
cp .env.example .env
```

Abra o arquivo `.env` e informe sua chave de acesso à API na variável `API_KEY`.

Instale as dependências do projeto:

```bash
uv sync
```

### 3. Executar a coleta

```bash
uv run python src/ingest.py
```

### 4. Gerar o diagnóstico dos dados

```bash
uv run quarto render analises/diagnostico.qmd
```

### 5. Transformar os dados

```bash
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

| Coluna                                                                        | Significado                                                                   |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `cargo_imputado`                                                              | `cargo.descricao` estava vazio e foi preenchido com "Não informado"           |
| `descricaoPoder_imputada`, `cnpj_imputada`, `sigla_imputada`, `nome_imputada` | O bloco `unidadeGestoraResponsavel.*` estava vazio e foi preenchido pela moda |

Para usar só os valores originais da fonte, filtre pelas flags (por exemplo, `cargo_imputado == False`). Para saber a que instituto a viagem pertence, use `orgao.sigla`, que é sempre preenchida.

Outras decisões do tratamento: a coluna `beneficiario.nis`, vazia em 100% dos registros, foi descartada. Em 3 viagens da unidade "Sigilosa", `beneficiario.cpfFormatado` e `cargo.codigoSIAPE` estão ausentes, e o contrato aceita isso apenas nessa unidade.

### data/quarentena/

O `transform.py` grava `data/quarentena/rejeitados.parquet` com as viagens que violam alguma regra do contrato, junto com a coluna `motivo` e a data de detecção (`detectado_em`). As linhas não são descartadas e podem ser reprocessadas. Na coleta de 30/09/2026 foram 2 viagens, ambas pelo motivo `devolucao_maior_que_viagem`.

Ao final da execução, o script imprime a quantidade de linhas em cada pasta e o resumo por motivo.
