"""Leva o dado de data/raw/ para data/trusted/, validando na fronteira.

Projeto: viagens a servico dos Institutos Federais do Nordeste
(API do Portal da Transparencia, endpoint /viagens).

    uv run python src/transform.py

Politica de falha: QUARENTENA. Linha reprovada vai para data/quarentena/ com
o motivo; a falha de estrutura (coluna a mais ou a menos) para tudo.

Dependencias: uv add pandas pyarrow pandera
"""

import json
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

DIR_RAW = Path("data/raw/portal_transparencia")
TRUSTED = Path("data/trusted/viagens.parquet")
QUARENTENA = Path("data/quarentena/rejeitados.parquet")

# A coleta cobre 2024 e 2025 (ver README)
JANELA = (pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31"))

COLUNAS_FINANCEIRAS = [
    "valorTotalDiarias",
    "valorTotalPassagem",
    "valorTotalViagem",
    "valorTotalDevolucao",
    "valorTotalRestituicao",
    "valorTotalTaxaAgenciamento",
    "valorMulta",
]
COLUNAS_UGR = [
    "unidadeGestoraResponsavel.descricaoPoder",
    "unidadeGestoraResponsavel.orgaoVinculado.cnpj",
    "unidadeGestoraResponsavel.orgaoVinculado.sigla",
    "unidadeGestoraResponsavel.orgaoVinculado.nome",
]

CONTRATO = DataFrameSchema(
    columns={
        # Acuracia: chave que nao repete
        "id": Column(str, nullable=False, unique=True),
        "viagem.numPcdp": Column(str, nullable=False),
        # Atualidade: janela da coleta
        "dataInicioAfastamento": Column(
            "datetime64[ns]",
            Check.in_range(*JANELA, error="data_inicio_fora_da_janela"),
            nullable=False,
        ),
        "dataFimAfastamento": Column("datetime64[ns]", nullable=False),
        # Consistencia: valores em reais nao podem ser negativos
        "valorTotalDiarias": Column(
            float, Check.greater_than_or_equal_to(0, error="diarias_negativas"), nullable=False
        ),
        "valorTotalPassagem": Column(
            float, Check.greater_than_or_equal_to(0, error="passagem_negativa"), nullable=False
        ),
        "valorTotalViagem": Column(
            float, Check.greater_than_or_equal_to(0, error="valor_viagem_negativo"), nullable=False
        ),
        "valorTotalDevolucao": Column(
            float, Check.greater_than_or_equal_to(0, error="devolucao_negativa"), nullable=False
        ),
        # Completude: ausentes imputados no diagnostico (aula-4)
        "cargo.descricao": Column(str, nullable=False),
        "unidadeGestoraResponsavel.nome": Column(str, nullable=False),
        "unidadeGestoraResponsavel.descricaoPoder": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoVinculado.cnpj": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoVinculado.sigla": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoVinculado.nome": Column(str, nullable=False),
        # Indicadoras criadas no diagnostico: precisam estar declaradas (strict)
        "cargo_imputado": Column(bool, nullable=False),
        "descricaoPoder_imputada": Column(bool, nullable=False),
        "cnpj_imputada": Column(bool, nullable=False),
        "sigla_imputada": Column(bool, nullable=False),
        "nome_imputada": Column(bool, nullable=False),
        # Valores em reais restantes (parseados em higienizar)
        "valorTotalRestituicao": Column(float, nullable=False),
        "valorTotalTaxaAgenciamento": Column(float, nullable=False),
        "valorMulta": Column(float, nullable=False),
        # Atributos da viagem
        "situacao": Column(str, nullable=False),
        "tipoViagem": Column(str, nullable=False),
        "viagem.pcdp": Column(str, nullable=False),
        "viagem.ano": Column(int, nullable=False),
        "viagem.motivo": Column(str, nullable=False),
        "viagem.urgenciaViagem": Column(str, nullable=False),
        # So preenchida quando a viagem e urgente: ausencia esperada
        "viagem.justificativaUrgente": Column(str, nullable=True),
        # Beneficiario, cargo e funcao
        # Ausentes so em viagem sigilosa: ver a regra de tabela no fim do contrato
        "beneficiario.cpfFormatado": Column(str, nullable=True),
        "beneficiario.nome": Column(str, nullable=False),
        "cargo.codigoSIAPE": Column(str, nullable=True),
        "funcao.codigoSIAPE": Column(str, nullable=False),
        "funcao.descricao": Column(str, nullable=False),
        # Orgao solicitante
        "orgao.nome": Column(str, nullable=False),
        "orgao.sigla": Column(str, nullable=False),
        "orgao.cnpj": Column(str, nullable=False),
        "orgao.codigoSIAFI": Column(str, nullable=False),
        "orgao.descricaoPoder": Column(str, nullable=False),
        "orgao.orgaoMaximo.codigo": Column(str, nullable=False),
        "orgao.orgaoMaximo.sigla": Column(str, nullable=False),
        "orgao.orgaoMaximo.nome": Column(str, nullable=False),
        # Orgao pagador
        "orgaoPagamento.nome": Column(str, nullable=False),
        "orgaoPagamento.sigla": Column(str, nullable=False),
        "orgaoPagamento.cnpj": Column(str, nullable=False),
        "orgaoPagamento.codigoSIAFI": Column(str, nullable=False),
        "orgaoPagamento.descricaoPoder": Column(str, nullable=False),
        "orgaoPagamento.orgaoMaximo.codigo": Column(str, nullable=False),
        "orgaoPagamento.orgaoMaximo.sigla": Column(str, nullable=False),
        "orgaoPagamento.orgaoMaximo.nome": Column(str, nullable=False),
        # Unidade gestora (restante do bloco)
        "unidadeGestoraResponsavel.codigo": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoVinculado.codigoSIAFI": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoMaximo.codigo": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoMaximo.sigla": Column(str, nullable=False),
        "unidadeGestoraResponsavel.orgaoMaximo.nome": Column(str, nullable=False),
    },
    checks=[
        # Regra de negocio 1: a viagem nao pode terminar antes de comecar.
        # Origem: logica do proprio processo (suposicao da equipe, nao fonte).
        # ~(fim < inicio) deixa passar NaT; o nullable da coluna cuida dele.
        Check(
            lambda df: ~(df["dataFimAfastamento"] < df["dataInicioAfastamento"]),
            error="data_fim_antes_do_inicio",
        ),
        # Regra de negocio 2: nao se devolve mais do que se gastou.
        # Suposicao da equipe;
        Check(
            lambda df: ~(df["valorTotalDevolucao"] > df["valorTotalViagem"]),
            error="devolucao_maior_que_viagem",
        ),
        # Regra de negocio 3: CPF e SIAPE do beneficiario so podem faltar em
        # viagem de unidade "Sigilosa". Origem: os 3 casos observados no dado,
        # todos dessa unidade. Que a omissao seja por sigilo e hipotese da
        # equipe, nao confirmada pela fonte.
        Check(
            lambda df: (
                df["beneficiario.cpfFormatado"].notna() & df["cargo.codigoSIAPE"].notna()
            )
            | (df["unidadeGestoraResponsavel.nome"] == "Sigilosa"),
            error="beneficiario_ausente_fora_de_sigilo",
        ),
    ],
    coerce=True,
    strict=True,
)


def _ler_numero(serie: pd.Series) -> pd.Series:
    """Converte '1.234,56' (formato BR) em float; numero ja numerico passa direto."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    limpo = serie.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    limpo = limpo.where(serie.notna())
    numero = pd.to_numeric(limpo, errors="coerce")
    ilegivel = numero.isna() & serie.notna()
    if ilegivel.any():
        raise ValueError(f"{ilegivel.sum()} valores nao numericos: {serie[ilegivel].head(3).tolist()}")
    return numero


def carregar(diretorio: Path) -> pd.DataFrame:
    """Le todos os JSON de data/raw/ e remove as linhas repetidas na integra."""
    arquivos = sorted(diretorio.rglob("*.json"))
    if not arquivos:
        raise SystemExit(f"nenhum .json em {diretorio.resolve()}")
    registros: list[dict] = []
    for arquivo in arquivos:
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
        if isinstance(conteudo.get("dados"), list):
            registros.extend(conteudo["dados"])
    df = pd.json_normalize(registros)
    # astype(str) so para comparar: evita erro com valores nao hasheaveis
    return df[~df.astype(str).duplicated()].reset_index(drop=True)


def ler_data(texto: pd.Series) -> pd.Series:
    """Aceita AAAA-MM-DD e DD/MM/AAAA, cada um pelo nome; um terceiro formato e erro.

    Nao usar format="mixed", dayfirst=True: o dayfirst vale tambem para ISO.
    """
    if pd.api.types.is_datetime64_any_dtype(texto):
        return texto
    iso = pd.to_datetime(texto, format="%Y-%m-%d", errors="coerce")
    br = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")
    data = iso.fillna(br)
    ilegivel = data.isna() & texto.notna()
    if ilegivel.any():
        raise ValueError(f"{ilegivel.sum()} datas fora dos dois formatos: {texto[ilegivel].head(3).tolist()}")
    return data


def higienizar(df: pd.DataFrame) -> pd.DataFrame:
    """Formato: datas para datetime, valores BR para float. Nao muda o que o dado afirma."""
    df = df.copy()
    # No JSON a ausencia pode vir como "" e nao como nulo. O diagnostico (que
    # passa por CSV) ja tratava "" como nulo; sem isto, o transform imputaria
    # menos e o contrato deixaria passar texto vazio.
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            vazio = df[col].notna() & df[col].astype(str).str.strip().eq("")
            df.loc[vazio, col] = pd.NA
    for col in ("dataInicioAfastamento", "dataFimAfastamento"):
        df[col] = ler_data(df[col])
    for col in COLUNAS_FINANCEIRAS:
        if col in df.columns:
            df[col] = _ler_numero(df[col])
    return df


def tratar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """As decisoes do diagnostico.qmd. Devolve (tratado, quarentena do diagnostico).

    Os suspeitos do diagnostico (valor negativo, data invertida) agora sao regras
    do CONTRATO, entao a quarentena daqui nasce vazia e o motivo vem do error=.
    """
    df = df.drop(columns=["beneficiario.nis"], errors="ignore")  # 100% ausente

    # cargo.descricao: MAR, texto fixo + indicadora
    df["cargo_imputado"] = df["cargo.descricao"].isna()
    df["cargo.descricao"] = df["cargo.descricao"].fillna("Não informado")

    # bloco unidadeGestoraResponsavel: MAR, moda + indicadora por coluna
    for col in COLUNAS_UGR:
        flag = f"{col.split('.')[-1]}_imputada"
        df[flag] = df[col].isna()
        df[col] = df[col].fillna(df[col].mode()[0])

    vazia = df.iloc[0:0].assign(motivo=pd.Series(dtype=str))
    return df, vazia


def validar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (aprovado, reprovado com motivo). Nao grava nada.

    lazy=True coleta todas as violacoes. O groupby por 'index' existe porque
    regra de tabela reprova a LINHA mas o Pandera reporta uma falha por celula.
    Falha sem linha (estrutura) para tudo, para o strict=True valer.
    """
    reprovados = [df.iloc[0:0].assign(motivo=pd.Series(dtype=str))]
    while True:
        try:
            return CONTRATO.validate(df, lazy=True), pd.concat(reprovados)
        except pa.errors.SchemaErrors as erro:
            falhas = erro.failure_cases
        de_linha = falhas.dropna(subset=["index"])
        if de_linha.empty:
            raise SystemExit(
                "contrato quebrado na estrutura, nada foi gravado:\n"
                + falhas[["column", "check", "failure_case"]].to_string(index=False)
            )
        motivo = de_linha.groupby("index")["check"].agg(lambda s: ", ".join(sorted(set(s))))
        reprovados.append(df.loc[motivo.index].assign(motivo=motivo))
        df = df.drop(index=motivo.index)


def main() -> None:
    tratado, quarentena_diag = tratar(higienizar(carregar(DIR_RAW)))
    aprovado, reprovado = validar(tratado)

    rejeitado = pd.concat([quarentena_diag, reprovado], ignore_index=True)
    rejeitado["detectado_em"] = pd.Timestamp.now(tz="UTC")

    TRUSTED.parent.mkdir(parents=True, exist_ok=True)
    aprovado.to_parquet(TRUSTED, index=False)

    if len(rejeitado):
        QUARENTENA.parent.mkdir(parents=True, exist_ok=True)
        rejeitado.to_parquet(QUARENTENA, index=False)

    print(f"trusted:    {len(aprovado):6d} linhas  ->  {TRUSTED}")
    print(f"quarentena: {len(rejeitado):6d} linhas  ->  {QUARENTENA}")
    for motivo, n in rejeitado["motivo"].value_counts().items():
        print(f"  {motivo:40} {n}")


if __name__ == "__main__":
    main()