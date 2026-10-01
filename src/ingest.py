import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.environ["API_BASE_URL"].rstrip("/")
API_ENDPOINT = os.environ["API_ENDPOINT"]
API_KEY = os.environ["API_KEY"]

ORGAOS_FILE = Path(os.environ["ORGAOS_FILE"])
ORGAOS_CODIGO_COL = os.environ["ORGAOS_CODIGO_COL"]
ORGAOS_NOME_COL = os.environ["ORGAOS_NOME_COL"]

DATA_INICIO = datetime.strptime(
    os.environ["DATA_INICIO"],
    "%d/%m/%Y",
).date()

DATA_FIM = datetime.strptime(
    os.environ["DATA_FIM"],
    "%d/%m/%Y",
).date()

MESES_POR_COLETA = int(os.environ["MESES_POR_COLETA"])
PAGE_SIZE = int(os.environ["PAGE_SIZE"])
REQUEST_TIMEOUT = int(os.environ["REQUEST_TIMEOUT"])
MAX_TENTATIVAS = int(os.environ["MAX_TENTATIVAS"])
BACKOFF_BASE = int(os.environ["BACKOFF_BASE"])

RAW_DIR = Path(os.environ["RAW_DIR"])


def validar_configuracao():
    if not API_KEY:
        raise ValueError(
            "API_KEY não configurada no arquivo .env."
        )

    if not ORGAOS_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo de órgãos não encontrado: {ORGAOS_FILE}"
        )

    if DATA_INICIO > DATA_FIM:
        raise ValueError(
            "DATA_INICIO não pode ser posterior a DATA_FIM."
        )

    if MESES_POR_COLETA != 1:
        raise ValueError(
            "MESES_POR_COLETA deve ser 1 para o endpoint /viagens."
        )


def carregar_orgaos():
    df = pd.read_csv(
        ORGAOS_FILE,
        dtype=str,
    )

    if ORGAOS_CODIGO_COL not in df.columns:
        raise ValueError(
            f"Coluna de código não encontrada: "
            f"{ORGAOS_CODIGO_COL}"
        )

    if ORGAOS_NOME_COL not in df.columns:
        raise ValueError(
            f"Coluna de nome não encontrada: "
            f"{ORGAOS_NOME_COL}"
        )

    return (
        df[
            [ORGAOS_CODIGO_COL, ORGAOS_NOME_COL]
        ]
        .dropna()
        .drop_duplicates()
    )


def adicionar_meses(data, quantidade):
    mes = data.month - 1 + quantidade
    ano = data.year + mes // 12
    mes = mes % 12 + 1

    dias_no_mes = [
        31,
        29 if ano % 4 == 0 and (
            ano % 100 != 0
            or ano % 400 == 0
        ) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]

    dia = min(
        data.day,
        dias_no_mes[mes - 1],
    )

    return data.replace(
        year=ano,
        month=mes,
        day=dia,
    )


def gerar_periodos():
    # O endpoint de viagens deve ser consultado em janelas mensais.
    periodos = []
    inicio = DATA_INICIO

    while inicio <= DATA_FIM:
        fim = (
            adicionar_meses(
                inicio,
                MESES_POR_COLETA,
            )
            - timedelta(days=1)
        )

        if fim > DATA_FIM:
            fim = DATA_FIM

        periodos.append(
            (inicio, fim)
        )

        inicio = fim + timedelta(days=1)

    return periodos


def requisitar(params):
    url = f"{API_BASE_URL}{API_ENDPOINT}"

    headers = {
        "chave-api-dados": API_KEY,
    }

    for tentativa in range(MAX_TENTATIVAS):
        resposta = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if resposta.status_code == 200:
            return resposta.json()

        if resposta.status_code in (401, 403):
            raise PermissionError(
                f"Credencial inválida ou acesso negado: "
                f"{resposta.status_code}"
            )

        if resposta.status_code == 429:
            # A API pode informar o tempo recomendado para nova tentativa.
            espera = int(
                resposta.headers.get(
                    "Retry-After",
                    BACKOFF_BASE ** tentativa,
                )
            )

            print(
                f"Limite de requisições atingido. "
                f"Aguardando {espera}s."
            )

            time.sleep(espera)
            continue

        if resposta.status_code >= 500:
            espera = BACKOFF_BASE ** tentativa

            print(
                f"Erro no servidor ({resposta.status_code}). "
                f"Tentativa {tentativa + 1}/"
                f"{MAX_TENTATIVAS}."
            )

            time.sleep(espera)
            continue

        raise RuntimeError(
            f"Erro HTTP {resposta.status_code}: "
            f"{resposta.text[:300]}"
        )

    raise RuntimeError(
        f"Falha após {MAX_TENTATIVAS} tentativas."
    )


def criar_parametros(
    codigo_orgao,
    data_inicio,
    data_fim,
    pagina,
):
    return {
        "dataIdaDe": data_inicio.strftime("%d/%m/%Y"),
        "dataIdaAte": data_fim.strftime("%d/%m/%Y"),
        "dataRetornoDe": data_inicio.strftime("%d/%m/%Y"),
        "dataRetornoAte": data_fim.strftime("%d/%m/%Y"),
        "codigoOrgao": codigo_orgao,
        "pagina": pagina,
        "tamanhoPagina": PAGE_SIZE,
    }


def coletar_paginas(
    codigo_orgao,
    data_inicio,
    data_fim,
):
    registros = []
    pagina = 1

    while True:
        params = criar_parametros(
            codigo_orgao,
            data_inicio,
            data_fim,
            pagina,
        )

        dados = requisitar(params)

        if not dados:
            break

        registros.extend(dados)

        if len(dados) < PAGE_SIZE:
            break

        pagina += 1

    return registros


def criar_caminho_raw(
    codigo_orgao,
    data_inicio,
    data_fim,
):
    pasta = RAW_DIR

    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )

    nome_arquivo = (
        f"viagens_{codigo_orgao}_"
        f"{data_inicio.strftime('%Y%m%d')}_"
        f"{data_fim.strftime('%Y%m%d')}.json"
    )

    return pasta / nome_arquivo


def criar_envelope(
    registros,
    codigo_orgao,
    nome_orgao,
    data_inicio,
    data_fim,
):
    return {
        "fonte": "Portal da Transparência",
        "endpoint": API_ENDPOINT,
        "coletado_em": datetime.now().astimezone().isoformat(),
        "parametros_coleta": {
            "codigoOrgao": codigo_orgao,
            "nomeOrgao": nome_orgao,
            "dataIdaDe": data_inicio.strftime("%d/%m/%Y"),
            "dataIdaAte": data_fim.strftime("%d/%m/%Y"),
            "dataRetornoDe": data_inicio.strftime("%d/%m/%Y"),
            "dataRetornoAte": data_fim.strftime("%d/%m/%Y"),
        },
        "quantidade_registros": len(registros),
        "dados": registros,
    }


def salvar_coleta(
    registros,
    codigo_orgao,
    nome_orgao,
    data_inicio,
    data_fim,
):
    caminho = criar_caminho_raw(
        codigo_orgao,
        data_inicio,
        data_fim,
    )

    if caminho.exists():
        return 0, caminho, False

    envelope = criar_envelope(
        registros,
        codigo_orgao,
        nome_orgao,
        data_inicio,
        data_fim,
    )

    caminho.write_text(
        json.dumps(
            envelope,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return len(registros), caminho, True


def preparar_coleta():
    validar_configuracao()

    orgaos = carregar_orgaos()
    periodos = gerar_periodos()

    return orgaos, periodos


def executar_coleta(
    orgaos,
    periodos,
):
    total_registros = 0
    total_coletas = 0
    total_ignoradas = 0

    for _, orgao in orgaos.iterrows():
        codigo = orgao[ORGAOS_CODIGO_COL]
        nome = orgao[ORGAOS_NOME_COL]

        for inicio, fim in periodos:
            print(
                f"Coletando {nome} ({codigo}) | "
                f"{inicio.strftime('%d/%m/%Y')} - "
                f"{fim.strftime('%d/%m/%Y')}"
            )

            registros = coletar_paginas(
                codigo,
                inicio,
                fim,
            )

            quantidade, caminho, gravado = salvar_coleta(
                registros,
                codigo,
                nome,
                inicio,
                fim,
            )

            if gravado:
                total_coletas += 1
                total_registros += quantidade

                print(
                    f"Registros: {quantidade} | "
                    f"Arquivo: {caminho}"
                )
            else:
                total_ignoradas += 1

                print(
                    f"Já coletado: {caminho}"
                )

    return {
        "orgaos": len(orgaos),
        "periodos": len(periodos),
        "coletas": total_coletas,
        "ignoradas": total_ignoradas,
        "registros": total_registros,
    }


def main():
    orgaos, periodos = preparar_coleta()

    print(
        f"Órgãos: {len(orgaos)} | "
        f"Períodos: {len(periodos)}"
    )

    resultado = executar_coleta(
        orgaos,
        periodos,
    )

    print()
    print("Coleta finalizada.")
    print(f"Órgãos processados: {resultado['orgaos']}")
    print(f"Períodos processados: {resultado['periodos']}")
    print(f"Coletas gravadas: {resultado['coletas']}")
    print(f"Coletas ignoradas: {resultado['ignoradas']}")
    print(f"Registros coletados: {resultado['registros']}")
    print(f"Dados salvos em: {RAW_DIR}")


if __name__ == "__main__":
    main()
