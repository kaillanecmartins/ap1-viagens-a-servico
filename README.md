# Análise de viagens a serviço dos Institutos Federais do Nordeste

Projeto desenvolvido para a atividade prática da Etapa 1 da disciplina de Introdução à Ciência de Dados.

O objetivo é coletar, organizar e analisar dados de viagens a serviço dos Institutos Federais de Educação, Ciência e Tecnologia do Nordeste, utilizando informações disponibilizadas pelo Portal da Transparência do Governo Federal.

## Objetivo da análise

Investigar a quantidade de viagens realizadas pelos Institutos Federais no ano de 2025 e identificar quais instituições registraram mais viagens no período.

A análise utiliza os dados coletados por meio da API do Portal da Transparência.

## Fonte dos dados

- **Fonte:** Portal da Transparência do Governo Federal
- **API:** API de Dados do Portal da Transparência
- **Endpoint utilizado:** `/viagens`
- **Período analisado:** janeiro a dezembro de 2025
- **Recorte:** Institutos Federais de Educação, Ciência e Tecnologia do Nordeste

Os dados são obtidos por meio de requisições à API. A coleta depende dos parâmetros exigidos pelo serviço e da disponibilidade dos dados.

## Tecnologias utilizadas

- Python
- uv
- pandas
- DuckDB
- requests
- python-dotenv
- Quarto

## Estrutura do projeto

```text
.
├── data/
│   ├── raw/
│   │   └── portal_transparencia/
│   ├── trusted/
│   └── quarentena/
├── src/
│   ├── ingest.py
│   └── transform.py
├── diagnostico.qmd
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

### Organização dos dados

- `data/raw/`: dados originais coletados da API.
- `data/trusted/`: dados tratados e preparados para análise.
- `data/quarentena/`: registros separados durante o tratamento por não atenderem às regras definidas.

Os dados brutos são gerados durante a execução da coleta e não são versionados no Git.

## Configuração do ambiente

### 1. Pré-requisitos

Instale:

- Python
- uv
- Git

### 2. Clonar o repositório

```bash
git clone https://github.com/kaillanecmartins/ap1-viagens-a-servico.git
cd ap1-viagens-a-servico
```

### 3. Configurar as variáveis de ambiente

Crie o arquivo `.env` a partir do modelo:

```bash
cp .env.example .env
```

No Windows PowerShell, também é possível copiar o arquivo com:

```powershell
Copy-Item .env.example .env
```

Preencha as variáveis necessárias no arquivo `.env`, incluindo a chave de acesso à API, caso seja exigida.

**Não envie o arquivo `.env` para o repositório.**

### 4. Instalar as dependências

```bash
uv sync
```

## Execução do projeto

Execute os comandos a partir da raiz do repositório.

### 1. Coletar os dados

```bash
uv run python src/ingest.py
```

O script realiza a coleta dos dados da API e salva os arquivos brutos em `data/raw/`.

### 2. Gerar o diagnóstico

```bash
uv run quarto render diagnostico.qmd
```

O diagnóstico apresenta uma análise inicial dos dados coletados, incluindo informações sobre estrutura, tipos, valores ausentes e possíveis problemas de qualidade.

### 3. Transformar os dados

```bash
uv run python src/transform.py
```

O script realiza o tratamento dos dados e salva os resultados na camada `data/trusted/`. Registros que não atendem às regras definidas podem ser direcionados para `data/quarentena/`.

## Resultados esperados

Ao executar o projeto, espera-se obter:

- Dados brutos das viagens coletados da API.
- Diagnóstico da qualidade e estrutura dos dados.
- Dados tratados e organizados na camada trusted.
- Informações que permitam analisar a quantidade de viagens por Instituto Federal do Nordeste em 2025.

## Observações

- A coleta depende da disponibilidade da API e dos limites de requisição definidos pelo serviço.
- Os resultados dependem dos órgãos selecionados e dos critérios de tratamento implementados.