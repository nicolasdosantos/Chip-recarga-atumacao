# gera data/example_data.xlsx - um exemplo FICTICIO, com a mesma estrutura
# de colunas da planilha real, mas sem nenhum dado da empresa. serve pra
# quem for rodar o projeto sem ter acesso ao Google Sheets do GrupoFly.
#
# roda com: python data/gerar_exemplo.py

from pathlib import Path

import pandas as pd

linhas = [
    # ---- fisicos ativos: precisam de recarga (data vencida) ----
    ("CLARO - chip exemplo 1", "Físico", "11999990001", "Time Comercial", "Ativo", "10/02/2026"),
    ("TIM - chip exemplo 2", "Físico", "11999990002", "Suporte", "Ativo", "15/01/2026"),
    # ---- fisico ativo: dentro do prazo, nao precisa ainda ----
    ("VIVO - chip exemplo 3", "Físico", "11999990003", "SDR - Exemplo", "Ativo", "05/09/2026"),
    # ---- fisico ativo: sinalizacao manual urgente ----
    ("XIAOMI - chip exemplo 4", "Físico", "11999990004", "Alertas automatizados", "Ativo", "RECARREGAR"),
    ("CLARO - chip exemplo 5", "Físico", "11999990005", "Gestor de contas - Exemplo", "Ativo", "RECARGA RECUSADA"),
    # ---- fisico ativo: data em formato alternativo (ainda reconhecivel) ----
    ("TIM - chip exemplo 6", "Físico", "11999990006", "Closer - Exemplo", "Ativo", "20.11.25"),
    # ---- fisico ativo: sem data -> pendente de analise ----
    ("VIVO - chip exemplo 7", "Físico", "11999990007", "Time RH", "Ativo", ""),
    # ---- fisico ativo: data incompleta (sem ano) -> pendente de analise ----
    ("CLARO - chip exemplo 8", "Físico", "11999990008", "SDR - Exemplo 2", "Ativo", "28/08"),
    # ---- fisico, mas nao ativo -> fora da regra ----
    ("TIM - chip exemplo 9", "Físico", "11999990009", "Antigo colaborador", "Banido", "01/01/2025"),
    ("VIVO - chip exemplo 10", "Físico", "11999990010", "Numero desativado", "cancelado", ""),
    # ---- numeros fixos/virtuais (Br DID) -> fora do escopo dessa automacao ----
    ("FIXO", "Br DID", "1899990001", "API oficial", "Ativo", "Assinatura"),
    ("FIXO", "Br DID", "1899990002", "Grupo de alertas", "Ativo", "Assinatura"),
    ("FIXO", "Cancelado Br DID", "1899990003", "", "Banido", ""),
    # ---- linha vazia/quebrada, pra testar a validacao ----
    ("", "", "", "", "", ""),
]

colunas = ["localização chip", "Tipo", "Número", "Uso", "Status", "Última recarga"]

df = pd.DataFrame(linhas, columns=colunas)
df["Aparelho"] = ""
df["Conta Google"] = ""
df["Local"] = ""
df["inicio"] = ""

caminho = Path(__file__).resolve().parent / "example_data.xlsx"
df.to_excel(caminho, index=False, sheet_name="Fly")

print(f"gerado em: {caminho}")
print(f"total de linhas: {len(df)}")
