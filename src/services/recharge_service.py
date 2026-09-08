# aqui mora a regra de negocio de verdade: pra cada chip (ja filtrado como
# Fisico + Ativo), decide se ele precisa de recarga, ta ok, ou se o dado ta
# ruim demais pra decidir (pendente de analise).
#
# regra (fechada com o Nicolas na fase 1):
#   - "RECARREGAR" ou "RECARGA RECUSADA" -> precisa recarga, urgente
#   - sem data / "-" / data ilegivel     -> pendente de analise
#   - data valida:
#         dias_sem_recarga >= intervalo  -> precisa recarga
#         caso contrario                 -> ok

from datetime import date, datetime

import pandas as pd

from src.config import settings


def _parse_data(valor: str) -> date | None:
    """tenta ler a data em qualquer um dos formatos que a planilha usa.
    se nao conseguir em nenhum, devolve None (quem chama decide o que fazer)"""
    for formato in settings.FORMATOS_DATA_ACEITOS:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    return None


def analisar_chip(linha: pd.Series, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()

    # celula realmente vazia no excel vira NaN (float) quando lida pelo
    # pandas - sem esse tratamento, "str(nan)" vira o texto literal "nan" e
    # a mensagem de erro fica confusa ("data em formato não reconhecido
    # (nan)") em vez do caso mais claro de "sem data preenchida"
    valor_original = linha.get(settings.COL_ULTIMA_RECARGA, "")
    valor_bruto = "" if pd.isna(valor_original) else str(valor_original).strip()

    base = {
        "identificacao": linha.get(settings.COL_IDENTIFICACAO, ""),
        "numero": linha.get(settings.COL_NUMERO, ""),
        "uso": linha.get(settings.COL_USO, ""),
        "ultima_recarga_bruta": valor_bruto,
    }

    # caso 1: ja tem um aviso manual dizendo que precisa recarregar
    if valor_bruto.upper() in settings.SINAIS_RECARGA_URGENTE:
        return {
            **base,
            "situacao": "precisa_recarga",
            "urgente": True,
            "dias_desde_recarga": None,
            "motivo": f"sinalizado manualmente como \"{valor_bruto}\"",
        }

    # caso 2: nao tem informacao nenhuma
    if valor_bruto in ("", "-"):
        return {
            **base,
            "situacao": "pendente_analise",
            "urgente": False,
            "dias_desde_recarga": None,
            "motivo": "sem data de última recarga preenchida",
        }

    # caso 3: tem alguma coisa escrita, mas nao é uma data que a gente reconhece
    data_recarga = _parse_data(valor_bruto)
    if data_recarga is None:
        return {
            **base,
            "situacao": "pendente_analise",
            "urgente": False,
            "dias_desde_recarga": None,
            "motivo": f"data em formato não reconhecido (\"{valor_bruto}\")",
        }

    # caso 4: data valida, agora e so contar os dias
    dias = (hoje - data_recarga).days

    if dias >= settings.RECARGA_INTERVALO_DIAS:
        return {
            **base,
            "situacao": "precisa_recarga",
            "urgente": False,
            "dias_desde_recarga": dias,
            "motivo": f"{dias} dias sem recarga (limite configurado: {settings.RECARGA_INTERVALO_DIAS})",
        }

    return {
        **base,
        "situacao": "ok",
        "urgente": False,
        "dias_desde_recarga": dias,
        "motivo": f"recarregado há {dias} dia(s), ainda dentro do prazo",
    }


def analisar_recargas(df: pd.DataFrame, hoje: date | None = None) -> dict:
    """roda analisar_chip em cada linha e ja separa tudo em grupos, alem de
    calcular o valor total que precisaria ser recarregado."""
    resultados = [analisar_chip(linha, hoje) for _, linha in df.iterrows()]

    precisam_recarga = [r for r in resultados if r["situacao"] == "precisa_recarga"]
    ok = [r for r in resultados if r["situacao"] == "ok"]
    pendentes = [r for r in resultados if r["situacao"] == "pendente_analise"]

    # urgente (RECARREGAR/RECUSADA) primeiro, depois quem ta a mais tempo sem recarga
    precisam_recarga.sort(key=lambda r: (not r["urgente"], -(r["dias_desde_recarga"] or 0)))

    valor_total = round(len(precisam_recarga) * settings.VALOR_MINIMO_RECARGA, 2)

    return {
        "precisam_recarga": precisam_recarga,
        "ok": ok,
        "pendentes_analise": pendentes,
        "valor_total": valor_total,
    }
