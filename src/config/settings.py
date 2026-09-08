# configuracao central do projeto. le tudo do .env, entao nenhum outro
# arquivo do projeto deveria usar os.environ diretamente - passa por aqui.

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # raiz do projeto
load_dotenv(BASE_DIR / ".env")

# --- Google Sheets ---
GOOGLE_SERVICE_ACCOUNT_FILE = BASE_DIR / os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SPREADSHEET_TAB_NAME = os.environ.get("SPREADSHEET_TAB_NAME", "Fly")

# a service account so precisa de leitura, entao usa o escopo mais restrito possivel
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# --- Regra de negocio (nada disso fica fixo no codigo) ---
RECARGA_INTERVALO_DIAS = int(os.environ.get("RECARGA_INTERVALO_DIAS", 30))
VALOR_MINIMO_RECARGA = float(os.environ.get("VALOR_MINIMO_RECARGA", 20.00))

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

# formatos de data que a planilha pode ter (tentamos nessa ordem)
FORMATOS_DATA_ACEITOS = ["%d/%m/%Y", "%d.%m.%y"]

# --- Discord (notificacao via PyAutoGUI, fase posterior) ---
DISCORD_ATIVADO = os.environ.get("DISCORD_ATIVADO", "false").strip().lower() == "true"
DISCORD_CONTATO_NOME = os.environ.get("DISCORD_CONTATO_NOME", "")
DISCORD_APP_ID = "com.discordapp.Discord"  # id do flatpak instalado nessa maquina

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
DISCORD_DELAY_DIGITACAO_MS = int(os.environ.get("DISCORD_DELAY_DIGITACAO_MS", 200))
