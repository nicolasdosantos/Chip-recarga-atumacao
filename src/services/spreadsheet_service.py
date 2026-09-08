# esse arquivo cuida de UMA coisa so: conectar no Google Sheets e trazer os
# dados da aba configurada como DataFrame do pandas. nao tem regra de
# negocio aqui, isso fica pros outros modulos (validators/recharge_service)

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from src.config import settings
from src.utils.exceptions import AbaNaoEncontradaError, PlanilhaIndisponivelError


def _autenticar():
    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE.exists():
        raise PlanilhaIndisponivelError(
            f"arquivo de credencial nao encontrado em {settings.GOOGLE_SERVICE_ACCOUNT_FILE}. "
            "confere se o .env ta apontando pro lugar certo e se o service_account.json existe."
        )

    creds = Credentials.from_service_account_file(
        str(settings.GOOGLE_SERVICE_ACCOUNT_FILE), scopes=settings.GOOGLE_SCOPES
    )
    return gspread.authorize(creds)


def buscar_dados() -> pd.DataFrame:
    """conecta no Sheets e devolve a aba inteira como DataFrame.
    lanca PlanilhaIndisponivelError ou AbaNaoEncontradaError se algo falhar
    (planilha sem acesso, id errado, aba com nome diferente etc)."""
    cliente = _autenticar()

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
