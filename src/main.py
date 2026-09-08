# ponto de entrada do projeto.
# fluxo completo: le a planilha -> valida estrutura -> separa linha vazia ->
# filtra Fisico+Ativo -> analisa regra de recarga -> gera e salva relatorio.
# tudo que acontece de importante fica registrado em logs/ (fase 5).
#
# roda com (a partir da raiz do projeto, com o venv ativado):
#   python -m src.main

from src.config import settings
from src.reports.report_generator import gerar_relatorio_texto, salvar_relatorio
from src.services.discord_service import enviar_mensagem_discord, montar_mensagem
from src.services.recharge_service import analisar_recargas
from src.services.spreadsheet_service import buscar_dados
from src.utils.exceptions import (
    AbaNaoEncontradaError,
    ColunaEsperadaAusenteError,
    NotificacaoDiscordError,
    PlanilhaIndisponivelError,
)
from src.utils.logger import get_logger
from src.validators.data_validator import (
    filtrar_fisicos_ativos,
    separar_linhas_validas,
    validar_estrutura,
)

logger = get_logger()

ANALISE_VAZIA = {"precisam_recarga": [], "ok": [], "pendentes_analise": [], "valor_total": 0.0}


def main():
    logger.info("=== iniciando automacao de recarga de chips ===")

    try:
        df = buscar_dados()
    except PlanilhaIndisponivelError as e:
        logger.error(f"planilha indisponivel: {e}")
        return
    except AbaNaoEncontradaError as e:
        logger.error(f"aba nao encontrada: {e}")
        return

    logger.info(f"planilha lida com sucesso: {len(df)} registro(s) encontrado(s)")

    try:
        validar_estrutura(df)
    except ColunaEsperadaAusenteError as e:
        logger.error(f"planilha com estrutura inesperada: {e}")
        return

    validas, invalidas = separar_linhas_validas(df)
    if not invalidas.empty:
        logger.warning(f"{len(invalidas)} registro(s) invalido(s)/vazio(s) ignorado(s)")

    fisicos_ativos = filtrar_fisicos_ativos(validas)
    logger.info(f"{len(fisicos_ativos)} chip(s) fisico(s) com status Ativo entraram na analise")

    if fisicos_ativos.empty:
        logger.warning("nenhum chip fisico ativo encontrado - nada pra recarregar")
        analise = ANALISE_VAZIA
    else:
        analise = analisar_recargas(fisicos_ativos)

        if analise["pendentes_analise"]:
            logger.warning(
                f"{len(analise['pendentes_analise'])} chip(s) sem data de ultima recarga legivel "
                "(entraram como pendente de analise, revisar manualmente)"
            )

        logger.info(f"{len(analise['precisam_recarga'])} chip(s) identificado(s) pra recarga")
        logger.info(f"valor total calculado: R$ {analise['valor_total']:.2f}")

    texto_relatorio = gerar_relatorio_texto(df, invalidas, fisicos_ativos, analise)
    caminho = salvar_relatorio(texto_relatorio)
    logger.info(f"relatorio salvo em: {caminho}")

    print("\n" + texto_relatorio)

    if settings.DISCORD_ATIVADO:
        try:
            mensagem = montar_mensagem(analise)
            enviar_mensagem_discord(mensagem)
            logger.info(f"notificacao enviada no discord pra '{settings.DISCORD_CONTATO_NOME}'")
        except NotificacaoDiscordError as e:
            logger.error(f"falha ao notificar no discord: {e}")
    else:
        logger.info("notificacao no discord desativada (DISCORD_ATIVADO=false)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # ultima linha de defesa: qualquer coisa que eu nao previ especificamente
        # (falha de rede, credencial expirada, etc) cai aqui em vez de estourar
        # um traceback cru pro usuario final
        logger.exception("falha inesperada durante a execucao da automacao")
