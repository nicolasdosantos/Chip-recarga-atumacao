# configuracao central do projeto. le tudo do .env, entao nenhum outro
# arquivo do projeto deveria usar os.environ diretamente - passa por aqui.
#
# importante: esse arquivo NUNCA deve lancar excecao ao ser importado (todo
# o resto do projeto depende dele pra sequer funcionar). se um valor do
# .env vier invalido (tipo RECARGA_INTERVALO_DIAS="abc"), a gente avisa no
# console e cai pro valor padrao, em vez de derrubar o programa inteiro
# antes mesmo do main.py ter chance de tratar qualquer coisa.

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # raiz do projeto
load_dotenv(BASE_DIR / ".env")


def _int_env(nome: str, padrao: int) -> int:
    bruto = os.environ.get(nome, "").strip()
    if not bruto:
        return padrao
    try:
        return int(bruto)
    except ValueError:
        print(f"[config] aviso: {nome}='{bruto}' no .env nao e um numero inteiro valido, usando {padrao}")
        return padrao


def _float_env(nome: str, padrao: float) -> float:
    bruto = os.environ.get(nome, "").strip()
    if not bruto:
        return padrao
    try:
        return float(bruto)
    except ValueError:
        print(f"[config] aviso: {nome}='{bruto}' no .env nao e um numero valido, usando {padrao}")
        return padrao


# --- Fonte dos dados ---
# "local"  -> le data/example_data.xlsx, nao precisa de credencial nenhuma
#             (é o que vem configurado no .env.example, pra dar pra rodar o
#             projeto assim que clonar, sem precisar montar Google Cloud)
# "sheets" -> le a planilha real do Google Sheets (uso de producao)
FONTE_DADOS = os.environ.get("FONTE_DADOS", "local").strip().lower()
if FONTE_DADOS not in ("local", "sheets"):
    print(f"[config] aviso: FONTE_DADOS='{FONTE_DADOS}' invalido no .env (use 'local' ou 'sheets'), usando 'local'")
    FONTE_DADOS = "local"

# --- Google Sheets (só é usado/exigido se FONTE_DADOS=sheets) ---
_service_account_env = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
GOOGLE_SERVICE_ACCOUNT_FILE = BASE_DIR / _service_account_env if _service_account_env else None
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "").strip()
SPREADSHEET_TAB_NAME = os.environ.get("SPREADSHEET_TAB_NAME", "Fly").strip() or "Fly"

# a service account so precisa de leitura, entao usa o escopo mais restrito possivel
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# --- Regra de negocio (nada disso fica fixo no codigo) ---
RECARGA_INTERVALO_DIAS = _int_env("RECARGA_INTERVALO_DIAS", 30)
if RECARGA_INTERVALO_DIAS < 0:
    print(f"[config] aviso: RECARGA_INTERVALO_DIAS={RECARGA_INTERVALO_DIAS} negativo nao faz sentido, usando 30")
    RECARGA_INTERVALO_DIAS = 30

VALOR_MINIMO_RECARGA = _float_env("VALOR_MINIMO_RECARGA", 20.00)
if VALOR_MINIMO_RECARGA < 0:
    print(f"[config] aviso: VALOR_MINIMO_RECARGA={VALOR_MINIMO_RECARGA} negativo nao faz sentido, usando 20.00")
    VALOR_MINIMO_RECARGA = 20.00

# --- Colunas da planilha (mapeamento definido na Fase 1) ---
COL_IDENTIFICACAO = "localização chip"
COL_TIPO = "Tipo"
COL_NUMERO = "Número"
COL_USO = "Uso"
COL_STATUS = "Status"
COL_ULTIMA_RECARGA = "Última recarga"

TIPO_FISICO = "Físico"
STATUS_ATIVO = "Ativo"

# valores da coluna "Última recarga" que nao sao data, mas ja indicam que
# precisa de recarga (alguem anotou isso manualmente)
SINAIS_RECARGA_URGENTE = {"RECARREGAR", "RECARGA RECUSADA"}

# --- Caminhos locais ---
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
RELATORIOS_DIR = BASE_DIR / "relatorios"
ARQUIVO_DADOS_LOCAL = DATA_DIR / "example_data.xlsx"  # usado quando FONTE_DADOS=local

# formatos de data que a planilha pode ter (tentamos nessa ordem)
FORMATOS_DATA_ACEITOS = ["%d/%m/%Y", "%d.%m.%y"]

# --- Discord (notificacao via automacao de interface - funciona em Linux e Windows) ---
DISCORD_ATIVADO = os.environ.get("DISCORD_ATIVADO", "false").strip().lower() == "true"
DISCORD_CONTATO_NOME = os.environ.get("DISCORD_CONTATO_NOME", "").strip()
DISCORD_APP_ID = "com.discordapp.Discord"  # id do flatpak (so usado no Linux)

# tempos de espera do fluxo de automacao do discord (em segundos)
# aumentei tudo de proposito - descobri na pratica que ir rapido demais faz
# a automacao clicar/digitar antes da tela terminar de responder, e isso
# ja causou mensagem indo pra conversa errada. preferi deixar mais lento e
# confiavel do que rapido e arriscado.
DISCORD_ESPERA_ABRIR_APP = 30          # tempo MAXIMO esperando a janela aparecer (poll de 1 em 1s, nao é sleep fixo)
DISCORD_ESPERA_FOCO = 3
DISCORD_ESPERA_ABRIR_BUSCA = 2         # tempo pro Ctrl+K abrir o campo de busca
DISCORD_ESPERA_FILTRAR_BUSCA = 3       # tempo pro discord filtrar os resultados depois de digitar o nome
DISCORD_ESPERA_ABRIR_CONVERSA = 3      # tempo pra conversa carregar depois do Enter
DISCORD_ESPERA_ENTRE_TENTATIVAS = 2
DISCORD_MAX_TENTATIVAS_ABRIR_CONVERSA = 3

# delay entre cada tecla ao digitar (em milissegundos). bem mais lento que o
# normal de proposito - digitar rapido demais parecia fazer a busca do
# discord nao acompanhar direito e cair em contato errado
DISCORD_DELAY_DIGITACAO_MS = _int_env("DISCORD_DELAY_DIGITACAO_MS", 200)
