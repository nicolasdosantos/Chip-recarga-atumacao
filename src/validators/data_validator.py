# validacao dos dados que vieram da planilha. aqui é só a parte "estrutural"
# (a planilha tem as colunas certas? tem linha vazia?) - a regra de quantos
# dias desde a ultima recarga fica no recharge_service (fase 3)

import pandas as pd

from src.config import settings
from src.utils.exceptions import ColunaEsperadaAusenteError

COLUNAS_OBRIGATORIAS = [
    settings.COL_IDENTIFICACAO,
    settings.COL_TIPO,
    settings.COL_NUMERO,
    settings.COL_STATUS,
    settings.COL_ULTIMA_RECARGA,
]


def validar_estrutura(df: pd.DataFrame) -> None:
    """confere se a planilha tem as colunas que a gente espera antes de
    processar qualquer linha. se um dia mudarem o nome de uma coluna la na
    planilha, prefiro travar aqui com uma mensagem clara do que quebrar
    em algum lugar aleatorio mais na frente."""
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ColunaEsperadaAusenteError(
            f"a planilha nao tem a(s) coluna(s) esperada(s): {', '.join(faltando)}"
        )


def _valor_vazio(valor) -> bool:
    # celula vazia no excel/sheets vira NaN (float) quando lida pelo pandas.
    # sem esse "pd.isna" primeiro, "str(nan).strip()" da o texto literal
    # "nan" (nao ""), e a linha deixava de ser detectada como vazia
    if pd.isna(valor):
        return True
    return str(valor).strip() == ""


def _linha_vazia(linha: pd.Series) -> bool:
    # linha sem identificacao e sem numero nao é um chip de verdade,
    # provavelmente é uma linha em branco no meio da planilha
    campos_chave = [settings.COL_IDENTIFICACAO, settings.COL_NUMERO]
    return all(_valor_vazio(linha.get(campo, "")) for campo in campos_chave)


def separar_linhas_validas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """tira do meio as linhas vazias/quebradas. devolve (validas, invalidas).
    isso NAO filtra por Tipo/Status ainda, só remove lixo estrutural."""
    validas = []
    invalidas = []

    for _, linha in df.iterrows():
        if _linha_vazia(linha):
            registro = linha.to_dict()
            registro["Motivo_Erro"] = "linha vazia (sem identificação e sem número)"
            invalidas.append(registro)
        else:
            validas.append(linha.to_dict())

    return pd.DataFrame(validas), pd.DataFrame(invalidas)


def filtrar_fisicos_ativos(df: pd.DataFrame) -> pd.DataFrame:
    """aplica o primeiro filtro da regra de negocio: só chip Físico e Status
    Ativo entram na analise de recarga (BR DID tem recarga automatica, fora
    do escopo; Standby/Banido/cancelado nao precisam de recarga)."""
    if df.empty:
        return df

    tipo = df[settings.COL_TIPO].astype(str).str.strip()
    status = df[settings.COL_STATUS].astype(str).str.strip()

    return df[(tipo == settings.TIPO_FISICO) & (status == settings.STATUS_ATIVO)]
