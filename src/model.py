"""Leva as viagens dos IFs do Nordeste de data/trusted/ para data/gold/, no modelo estrela.
 
Adaptado do model.py do RetailCo (aula de Star Schema: aplicacao) ao desenho do
estrela.qmd da equipe. Roda depois do transform.py:
 
    uv run python src/model.py
 
Ordem (Kimball e Ross, 2013, cap. 20):
 
1. dimensoes()        dim_data, dim_instituto e dim_classificacao_viagem. A
                      dim_data cobre do primeiro ao ultimo dia, olhando as DUAS
                      datas da viagem (inicio e fim), inclusive os dias sem viagem
2. conferir_chaves()  toda chave natural da trusted existe na dimensao? Se
                      faltar alguma, para aqui, antes de existir a fato
3. fatos()            fato_viagem, com a chave natural trocada pela substituta
4. conferir_fatos()   contagem de linhas e soma de cada medida, gold x trusted
5. agregada()         fato_viagem_duracao, derivada da fato_viagem e conferida
6. gravar()           um arquivo por tabela em data/gold/, relido em seguida
 
Qualquer conferencia que nao bate para o script, e nada e gravado: as tabelas
vivem na memoria ate o passo 6. A troca de chave e por LEFT JOIN, nunca JOIN.
 
Dependencia: uv add duckdb
"""
 
from pathlib import Path
 
import duckdb
 
TRUSTED = Path("data/trusted/viagens.parquet")
DIR_GOLD = Path("data/gold")
 
TABELAS_GOLD = (
    "dim_data",
    "dim_instituto",
    "dim_classificacao_viagem",
    "fato_viagem",
    "fato_viagem_duracao",
)
 
# Duracao em dias, contando o dia de inicio e o de fim: viagem de um dia so = 1.
DURACAO = "date_diff('day', data_inicio, data_fim) + 1"
 
# Medidas da fato (todas aditivas): coluna na fato -> coluna na trusted
MEDIDAS = {
    "valor_total_viagem": "valorTotalViagem",
    "valor_total_diarias": "valorTotalDiarias",
    "valor_total_passagem": "valorTotalPassagem",
    "valor_total_devolucao": "valorTotalDevolucao",
    "valor_total_restituicao": "valorTotalRestituicao",
    "valor_total_taxa_agenciamento": "valorTotalTaxaAgenciamento",
    "valor_multa": "valorMulta",
}
 
# (o que se confere, dimensao, condicao da juncao, coluna da dimensao nunca nula)
CHAVES = [
    ("viagens.data_inicio", "dim_data", "d.data = v.data_inicio", "data"),
    ("viagens.data_fim", "dim_data", "d.data = v.data_fim", "data"),
    ("viagens.instituto_sigla", "dim_instituto", "d.sigla = v.instituto_sigla", "instituto_sk"),
    (
        "viagens.tipo+situacao+urgencia",
        "dim_classificacao_viagem",
        "d.tipo_viagem = v.tipo_viagem AND d.situacao = v.situacao "
        "AND d.urgencia_viagem = v.urgencia_viagem",
        "classificacao_sk",
    ),
]
 
# (o que se confere, na trusted, no gold)
CONFERENCIA = (
    [
        ("linhas de viagens", "SELECT COUNT(*) FROM viagens", "SELECT COUNT(*) FROM fato_viagem"),
        ("duracao (dias)", f"SELECT SUM({DURACAO}) FROM viagens", "SELECT SUM(duracao_dias) FROM fato_viagem"),
    ]
    + [
        (nome, f"SELECT SUM({nome}) FROM viagens", f"SELECT SUM({nome}) FROM fato_viagem")
        for nome in MEDIDAS
    ]
)
 
 
def parar(mensagem: str) -> None:
    raise SystemExit(f"{mensagem}\nnada foi gravado em {DIR_GOLD}/")
 
 
def abrir() -> duckdb.DuckDBPyConnection:
    """Banco em memoria, com a view 'viagens' (nomes sem ponto) sobre a trusted."""
    if not TRUSTED.exists():
        raise SystemExit(f"{TRUSTED} nao encontrado: rode antes o src/transform.py")
    con = duckdb.connect()
    medidas = ",\n            ".join(f'"{origem}" AS {nome}' for nome, origem in MEDIDAS.items())
    con.execute(
        f"""
        CREATE VIEW viagens AS
        SELECT id::VARCHAR AS id,
               "viagem.numPcdp"::VARCHAR AS num_pcdp,
               dataInicioAfastamento::DATE AS data_inicio,
               dataFimAfastamento::DATE AS data_fim,
               "orgao.sigla" AS instituto_sigla,
               "orgao.nome" AS instituto_nome,
               tipoViagem AS tipo_viagem,
               situacao,
               "viagem.urgenciaViagem" AS urgencia_viagem,
               {medidas}
        FROM read_parquet('{TRUSTED.as_posix()}')
        """
    )
    return con
 
 
def uma_linha_por_membro(con: duckdb.DuckDBPyConnection, tabela: str, chave: str) -> None:
    """A chave substituta so se atribui se cada membro tiver uma linha so."""
    linhas, distintos = con.sql(f"SELECT COUNT(*), COUNT(DISTINCT {chave}) FROM {tabela}").fetchall()[0]
    if linhas != distintos:
        parar(f"{tabela}: {linhas} linhas para {distintos} valores de {chave}")
 
 
def dimensoes(con: duckdb.DuckDBPyConnection) -> None:
    """As tres dimensoes. ROW_NUMBER() numera pela ordem da chave natural.
 
    A dim_data se gera do primeiro ao ultimo dia, e nao se tira das datas que
    aparecem nas viagens. Como a fato aponta para ela duas vezes (inicio e fim),
    o intervalo vai da menor data de inicio a maior data de fim. O
    generate_series inclui o ultimo dia; o range, nao.
    """
    con.execute(
        """
        CREATE TABLE dim_data AS
        SELECT dia::DATE AS data, year(dia) AS ano, month(dia) AS mes, day(dia) AS dia
        FROM generate_series(
            (SELECT MIN(LEAST(data_inicio, data_fim)) FROM viagens),
            (SELECT MAX(GREATEST(data_inicio, data_fim)) FROM viagens),
            INTERVAL 1 DAY) AS t(dia)
        """
    )
    con.execute(
        """
        CREATE TABLE dim_instituto AS
        SELECT ROW_NUMBER() OVER (ORDER BY instituto_sigla) AS instituto_sk,
               instituto_sigla AS sigla, instituto_nome AS nome
        FROM (SELECT DISTINCT instituto_sigla, instituto_nome FROM viagens)
        """
    )
    con.execute(
        """
        CREATE TABLE dim_classificacao_viagem AS
        SELECT ROW_NUMBER() OVER (ORDER BY tipo_viagem, situacao, urgencia_viagem) AS classificacao_sk,
               tipo_viagem, situacao, urgencia_viagem
        FROM (SELECT DISTINCT tipo_viagem, situacao, urgencia_viagem FROM viagens)
        """
    )
    # Uma sigla com dois nomes na trusted faria a fato duplicar viagens
    uma_linha_por_membro(con, "dim_instituto", "sigla")
 
 
def conferir_chaves(con: duckdb.DuckDBPyConnection) -> None:
    """Antes da troca: toda chave natural da trusted tem linha na dimensao?
 
    Conta linhas, e nao chaves distintas: e o que se perderia da fato.
    """
    print("linhas cuja chave nao esta na dimensao, antes da troca:")
    faltando = 0
    for rotulo, dimensao, condicao, coluna in CHAVES:
        n = con.sql(
            f"SELECT COUNT(*) FROM viagens v LEFT JOIN {dimensao} d ON {condicao} WHERE d.{coluna} IS NULL"
        ).fetchall()[0][0]
        print(f"  {rotulo:32} -> {dimensao:26} {n:6d}")
        faltando += n
    if faltando:
        parar(f"{faltando} linhas sem chave na dimensao: corrija a dimensao antes de construir a fato")
 
 
def fatos(con: duckdb.DuckDBPyConnection) -> None:
    """A fato, com a chave substituta no lugar da natural.
 
    id e num_pcdp ficam: sao a dimensao degenerada, sem tabela para onde
    apontar. As datas sao a propria chave da dim_data (dois papeis: inicio e fim).
    """
    medidas = ",\n               ".join(f"v.{nome}" for nome in MEDIDAS)
    con.execute(
        f"""
        CREATE TABLE fato_viagem AS
        SELECT v.id, v.num_pcdp, di.data AS data_inicio, df.data AS data_fim,
               i.instituto_sk, c.classificacao_sk,
               {DURACAO.replace('data_inicio', 'v.data_inicio').replace('data_fim', 'v.data_fim')} AS duracao_dias,
               {medidas}
        FROM viagens v
        LEFT JOIN dim_data di ON di.data = v.data_inicio
        LEFT JOIN dim_data df ON df.data = v.data_fim
        LEFT JOIN dim_instituto i ON i.sigla = v.instituto_sigla
        LEFT JOIN dim_classificacao_viagem c
               ON c.tipo_viagem = v.tipo_viagem AND c.situacao = v.situacao
              AND c.urgencia_viagem = v.urgencia_viagem
        ORDER BY v.id
        """
    )
    nulas = con.sql(
        """
        SELECT COUNT(*) FROM fato_viagem
        WHERE data_inicio IS NULL OR data_fim IS NULL OR instituto_sk IS NULL
           OR classificacao_sk IS NULL OR duracao_dias IS NULL
        """
    ).fetchall()[0][0]
    if nulas:
        parar(f"{nulas} linhas da fato com chave (ou duracao) nula")
 
 
def conferir_fatos(con: duckdb.DuckDBPyConnection) -> None:
    """Contagem e soma de cada medida, gold contra trusted. Tem de bater no centavo."""
    print("\nconferencia da fato contra a trusted:")
    print(f"  {'':32} {'trusted':>18} {'gold':>18}")
    diferentes = []
    for medida, na_trusted, no_gold in CONFERENCIA:
        trusted, gold = con.sql(f"SELECT ({na_trusted}), ({no_gold})").fetchall()[0]
        trusted, gold = float(trusted or 0), float(gold or 0)
        print(f"  {medida:32} {trusted:18.2f} {gold:18.2f}")
        if abs(trusted - gold) >= 0.01:
            diferentes.append(medida)
    if diferentes:
        parar(f"o gold nao bate com a trusted em: {', '.join(diferentes)}")
 
 
def agregada(con: duckdb.DuckDBPyConnection) -> None:
    """Uma linha por ano, instituto, tipo de viagem e faixa de duracao.
 
    Sai da fato_viagem (nao da trusted), para as duas nao poderem divergir. A
    media e a mediana sao do grupo e nao se somam entre grupos.
    """
    con.execute(
        """
        CREATE TABLE fato_viagem_duracao AS
        SELECT d.ano, f.instituto_sk, c.tipo_viagem,
               CASE WHEN f.duracao_dias = 1 THEN '1'
                    WHEN f.duracao_dias <= 3 THEN '2–3'
                    WHEN f.duracao_dias <= 7 THEN '4–7'
                    ELSE '8+' END AS faixa_duracao,
               COUNT(*) AS quantidade_viagens,
               SUM(f.duracao_dias)::BIGINT AS total_dias,
               SUM(f.valor_total_viagem) AS custo_total,
               SUM(f.valor_total_viagem) / COUNT(*) AS custo_medio,
               MEDIAN(f.valor_total_viagem) AS custo_mediano
        FROM fato_viagem f
        LEFT JOIN dim_data d ON d.data = f.data_inicio
        LEFT JOIN dim_classificacao_viagem c USING (classificacao_sk)
        GROUP BY ALL ORDER BY ano, instituto_sk, tipo_viagem, faixa_duracao
        """
    )
    atomica = con.sql(
        "SELECT COUNT(*), SUM(duracao_dias), SUM(valor_total_viagem) FROM fato_viagem"
    ).fetchall()[0]
    agregada = con.sql(
        "SELECT SUM(quantidade_viagens), SUM(total_dias), SUM(custo_total) FROM fato_viagem_duracao"
    ).fetchall()[0]
    if any(abs(float(a) - float(b)) >= 0.01 for a, b in zip(atomica, agregada)):
        parar(f"a agregada nao bate com a fato_viagem: {agregada} contra {atomica}")
    print(f"\nagregada confere com a fato_viagem: {int(agregada[0])} viagens, "
          f"{int(agregada[1])} dias, R$ {float(agregada[2]):.2f}")
 
 
def gravar(con: duckdb.DuckDBPyConnection) -> None:
    """Uma tabela por arquivo Parquet, e a releitura de cada um."""
    DIR_GOLD.mkdir(parents=True, exist_ok=True)
    print(f"\ngold  ->  {DIR_GOLD}/")
    for tabela in TABELAS_GOLD:
        caminho = DIR_GOLD / f"{tabela}.parquet"
        con.execute(f"COPY {tabela} TO '{caminho.as_posix()}' (FORMAT parquet)")
        relidas = con.sql(f"SELECT COUNT(*) FROM '{caminho.as_posix()}'").fetchall()[0][0]
        esperadas = con.sql(f"SELECT COUNT(*) FROM {tabela}").fetchall()[0][0]
        if relidas != esperadas:
            raise SystemExit(f"{tabela}: gravou {esperadas} linhas e leu {relidas}")
        print(f"  {tabela:26} {relidas:7d} linhas")
 
 
def main() -> None:
    con = abrir()
    dimensoes(con)
    conferir_chaves(con)
    fatos(con)
    conferir_fatos(con)
    agregada(con)
    gravar(con)
 
 
if __name__ == "__main__":
    main()
 