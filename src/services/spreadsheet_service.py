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
    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
        raise PlanilhaIndisponivelError(
            "GOOGLE_SERVICE_ACCOUNT_FILE nao configurado no .env. se voce so quer testar o "
            "projeto sem configurar o Google Cloud, deixe FONTE_DADOS=local no .env."
        )

    if not settings.GOOGLE_SERVICE_ACCOUNT_FILE.exists():
        raise PlanilhaIndisponivelError(
            f"arquivo de credencial nao encontrado em {settings.GOOGLE_SERVICE_ACCOUNT_FILE}. "
            "confere o GOOGLE_SERVICE_ACCOUNT_FILE no .env."
        )

    try:
        creds = Credentials.from_service_account_file(
            str(settings.GOOGLE_SERVICE_ACCOUNT_FILE), scopes=settings.GOOGLE_SCOPES
        )
    except (ValueError, KeyError) as e:
        # acontece quando o arquivo existe mas nao é um JSON de service
        # account valido (corrompido, baixado errado, é outro tipo de
        # credencial, etc)
        raise PlanilhaIndisponivelError(
            f"o arquivo {settings.GOOGLE_SERVICE_ACCOUNT_FILE} nao parece ser uma chave de "
            f"service account valida: {e}"
        )

    try:
        return gspread.authorize(creds)
    except Exception as e:
        raise PlanilhaIndisponivelError(f"nao consegui autenticar no Google: {e}")


def _buscar_do_sheets() -> pd.DataFrame:
    if not settings.SPREADSHEET_ID:
        raise PlanilhaIndisponivelError("SPREADSHEET_ID nao configurado no .env.")

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
    except Exception as e:
        # cobre falha de rede (sem internet, DNS, timeout etc) e qualquer
        # outra coisa que a gente nao previu especificamente - melhor virar
        # um erro claro do que um traceback cru
        raise PlanilhaIndisponivelError(f"nao consegui conectar no Google Sheets: {e}")

    try:
        aba = planilha.worksheet(settings.SPREADSHEET_TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        try:
            abas_existentes = [w.title for w in planilha.worksheets()]
        except Exception:
            abas_existentes = "(nao consegui listar)"
        raise AbaNaoEncontradaError(
            f"aba '{settings.SPREADSHEET_TAB_NAME}' nao existe nessa planilha. "
            f"abas disponiveis: {abas_existentes}"
        )

    try:
        registros = aba.get_all_records()
    except Exception as e:
        raise PlanilhaIndisponivelError(f"erro lendo os dados da aba '{settings.SPREADSHEET_TAB_NAME}': {e}")

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
        # pandas lanca ValueError especificamente quando o nome da aba nao existe
        raise AbaNaoEncontradaError(
            f"a aba '{settings.SPREADSHEET_TAB_NAME}' nao existe no arquivo local "
            f"{settings.ARQUIVO_DADOS_LOCAL}."
        )
    except Exception as e:
        # arquivo corrompido, nao é um .xlsx de verdade, sem permissao de leitura etc
        raise PlanilhaIndisponivelError(
            f"nao consegui ler o arquivo local {settings.ARQUIVO_DADOS_LOCAL}: {e}"
        )


def buscar_dados() -> pd.DataFrame:
    """devolve os dados como DataFrame, vindos do Sheets ou do arquivo local
    dependendo do FONTE_DADOS configurado. lanca PlanilhaIndisponivelError ou
    AbaNaoEncontradaError se algo falhar."""
    if settings.FONTE_DADOS == "local":
        return _buscar_do_arquivo_local()
    return _buscar_do_sheets()
