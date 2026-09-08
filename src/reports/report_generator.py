# monta o texto final do relatorio, no formato que o Nicolas desenhou.
# esse arquivo so formata - quem calcula tudo é o recharge_service, aqui é
# so pegar o resultado pronto e escrever bonito.

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import settings


def _reais(valor: float) -> str:
    # troca ponto por virgula pra ficar no formato br (R$ 20,00)
    return f"R$ {valor:.2f}".replace(".", ",")


def gerar_relatorio_texto(
    df_original: pd.DataFrame,
    df_invalidas: pd.DataFrame,
    df_fisicos_ativos: pd.DataFrame,
    analise: dict,
) -> str:
    agora = datetime.now()
    linhas = []

    linhas.append("RELATÓRIO DE RECARGAS")
    linhas.append("")
    linhas.append(f"Data da execução: {agora.strftime('%d/%m/%Y %H:%M')}")
    linhas.append("")
    linhas.append(f"Total de registros analisados: {len(df_original)}")
    linhas.append(f"Chips físicos analisados: {len(df_fisicos_ativos)}")
    linhas.append(f"Chips que precisam de recarga: {len(analise['precisam_recarga'])}")
    linhas.append("")
    linhas.append(f"Valor mínimo por recarga: {_reais(settings.VALOR_MINIMO_RECARGA)}")
    linhas.append(f"Valor total necessário: {_reais(analise['valor_total'])}")
    linhas.append("")

    if analise["precisam_recarga"]:
        linhas.append("CHIPS QUE PRECISAM DE RECARGA:")
        linhas.append("")
        for chip in analise["precisam_recarga"]:
            tag = " [URGENTE]" if chip["urgente"] else ""
            dias = chip["dias_desde_recarga"]
            linhas.append(f"- Identificação: {chip['identificacao']}{tag}")
            linhas.append(f"  Última recarga: {chip['ultima_recarga_bruta'] or '(vazio)'}")
            linhas.append(f"  Dias desde a última recarga: {dias if dias is not None else 'N/A'}")
            linhas.append("")

    if analise["pendentes_analise"]:
        linhas.append("PENDENTES DE ANÁLISE (revisar manualmente):")
        linhas.append("")
        for chip in analise["pendentes_analise"]:
            linhas.append(f"- Identificação: {chip['identificacao']}")
            linhas.append(f"  Motivo: {chip['motivo']}")
            linhas.append("")

    if not df_invalidas.empty:
        linhas.append(f"Linhas ignoradas (vazias/quebradas na planilha): {len(df_invalidas)}")
        linhas.append("")

    return "\n".join(linhas).rstrip() + "\n"


def salvar_relatorio(texto: str) -> Path:
    settings.RELATORIOS_DIR.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    caminho = settings.RELATORIOS_DIR / nome_arquivo
    caminho.write_text(texto, encoding="utf-8")
    return caminho
