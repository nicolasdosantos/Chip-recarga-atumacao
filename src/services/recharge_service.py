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


def _texto_seguro(valor) -> str:
    """converte pra string tratando NaN do pandas como vazio (em vez do
    texto literal "nan"), pra nao vazar isso pro relatorio/mensagem final."""
    return "" if pd.isna(valor) else str(valor).strip()


def _extrair_data(valor_original) -> tuple[date | None, str]:
    """tenta chegar numa data a partir do valor cru da celula, e tambem
    devolve uma versao em texto (pro relatorio mostrar o que tinha lá).

    a celula pode vir de duas formas bem diferentes:
    - já como um objeto de data de verdade (datetime/Timestamp), se a
      coluna "Última recarga" estiver formatada como data no Sheets/Excel
    - como texto (a maioria dos casos aqui), que a gente tenta ler nos
      formatos configurados em FORMATOS_DATA_ACEITOS

    sem tratar o primeiro caso, uma coluna formatada como data faria TODO
    chip cair silenciosamente em "pendente de analise", mesmo com data
    perfeitamente valida."""
    if pd.isna(valor_original):
        return None, ""

    if isinstance(valor_original, pd.Timestamp):
        data = valor_original.date()
        return data, data.strftime("%d/%m/%Y")

    if isinstance(valor_original, datetime):
        data = valor_original.date()
        return data, data.strftime("%d/%m/%Y")

    if isinstance(valor_original, date):
        return valor_original, valor_original.strftime("%d/%m/%Y")

    texto = str(valor_original).strip()
    for formato in settings.FORMATOS_DATA_ACEITOS:
        try:
            return datetime.strptime(texto, formato).date(), texto
        except ValueError:
            continue

    return None, texto


def analisar_chip(linha: pd.Series, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()

    valor_original = linha.get(settings.COL_ULTIMA_RECARGA, "")
    data_recarga, valor_bruto = _extrair_data(valor_original)

    base = {
        "identificacao": _texto_seguro(linha.get(settings.COL_IDENTIFICACAO, "")),
        "numero": _texto_seguro(linha.get(settings.COL_NUMERO, "")),
        "uso": _texto_seguro(linha.get(settings.COL_USO, "")),
        "ultima_recarga_bruta": valor_bruto,
    }

    # caso 1: ja tem um aviso manual dizendo que precisa recarregar (isso so
    # faz sentido pra celula de texto, nao pra data de verdade)
    if data_recarga is None and valor_bruto.upper() in settings.SINAIS_RECARGA_URGENTE:
        return {
            **base,
            "situacao": "precisa_recarga",
            "urgente": True,
            "dias_desde_recarga": None,
            "motivo": f"sinalizado manualmente como \"{valor_bruto}\"",
        }

    # caso 2: nao tem informacao nenhuma
    if data_recarga is None and valor_bruto in ("", "-"):
        return {
            **base,
            "situacao": "pendente_analise",
            "urgente": False,
            "dias_desde_recarga": None,
            "motivo": "sem data de última recarga preenchida",
        }

    # caso 3: tem alguma coisa escrita, mas nao é uma data que a gente reconhece
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
