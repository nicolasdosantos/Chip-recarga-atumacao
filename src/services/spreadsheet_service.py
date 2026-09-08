# esse arquivo cuida de UMA coisa so: trazer os dados (de onde for) como
# DataFrame do pandas. nao tem regra de negocio aqui, isso fica pros outros
# modulos (validators/recharge_service).
#
# tem 2 fontes possiveis, controladas pelo FONTE_DADOS no .env:
#   - "local"  -> le data/example_data.xlsx (nao precisa de credencial
#                 nenhuma - é o que vem configurado por padrao, pra dar pra
#                 rodar o projeto assim que clona, sem montar Google Cloud)
#   - "sheets" -> le a planilha real do Google Sheets via service account
#                 (uso de producao, o que a gente realmente usa no dia a dia)

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from src.config import settings
from src.utils.exceptions import AbaNaoEncontradaError, PlanilhaIndisponivelError


def _autenticar_google():
    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE or not settings.GOOGLE_SERVICE_ACCOUNT_FILE.exists():
        raise PlanilhaIndisponivelError(
            "arquivo de credencial da service account nao encontrado (confere o "
            "GOOGLE_SERVICE_ACCOUNT_FILE no .env). se voce so quer testar o projeto sem "
            "configurar o Google Cloud, deixe FONTE_DADOS=local no .env."
        )

    creds = Credentials.from_service_account_file(
        str(settings.GOOGLE_SERVICE_ACCOUNT_FILE), scopes=settings.GOOGLE_SCOPES
    )
    return gspread.authorize(creds)


def _buscar_do_sheets() -> pd.DataFrame:
    cliente = _autenticar_google()

    try:
        planilha = cliente.open_by_key(settings.SPREADSHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        raise PlanilhaIndisponivelError(
            f"planilha com ID '{settings.SPREADSHEET_ID}' nao encontrada (ou sem acesso). "
            "confere se o ID esta certo e se a planilha foi compartilhada com a service account."
        )
    except gspread.exceptions.APIError as e:
        raise PlanilhaIndisponivelError(f"erro da API do Google Sheets: {e}")

    try:
        aba = planilha.worksheet(settings.SPREADSHEET_TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        abas_existentes = [w.title for w in planilha.worksheets()]
        raise AbaNaoEncontradaError(
            f"aba '{settings.SPREADSHEET_TAB_NAME}' nao existe nessa planilha. "
            f"abas disponiveis: {abas_existentes}"
        )

    registros = aba.get_all_records()
    return pd.DataFrame(registros)


def _buscar_do_arquivo_local() -> pd.DataFrame:
    if not settings.ARQUIVO_DADOS_LOCAL.exists():
        raise PlanilhaIndisponivelError(
            f"FONTE_DADOS=local mas nao achei o arquivo {settings.ARQUIVO_DADOS_LOCAL}. "
            "roda 'python data/gerar_exemplo.py' pra gerar ele."
        )

    try:
        return pd.read_excel(settings.ARQUIVO_DADOS_LOCAL, sheet_name=settings.SPREADSHEET_TAB_NAME)
    except ValueError:
        raise AbaNaoEncontradaError(
            f"a aba '{settings.SPREADSHEET_TAB_NAME}' nao existe no arquivo local "
            f"{settings.ARQUIVO_DADOS_LOCAL}."
        )


def buscar_dados() -> pd.DataFrame:
    """devolve os dados como DataFrame, vindos do Sheets ou do arquivo local
    dependendo do FONTE_DADOS configurado. lanca PlanilhaIndisponivelError ou
    AbaNaoEncontradaError se algo falhar."""
    if settings.FONTE_DADOS == "local":
        return _buscar_do_arquivo_local()
    return _buscar_do_sheets()
