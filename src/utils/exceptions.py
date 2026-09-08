# excecoes proprias do projeto. uso isso em vez de deixar o erro cru do
# gspread/pandas estourar la na frente, assim fica mais facil saber o que
# aconteceu de verdade quando alguma coisa da planilha muda ou falha.


class PlanilhaIndisponivelError(Exception):
    """nao deu pra conectar ou abrir a planilha (rede, permissao, id errado etc)"""


class AbaNaoEncontradaError(Exception):
    """a aba configurada em SPREADSHEET_TAB_NAME nao existe na planilha"""


class ColunaEsperadaAusenteError(Exception):
    """a planilha nao tem alguma coluna que o codigo espera que exista"""


class NotificacaoDiscordError(Exception):
    """deu ruim tentando abrir o discord ou mandar a mensagem via automacao"""
