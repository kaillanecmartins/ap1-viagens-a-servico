import os
from datetime import datetime
from pathlib import Path

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