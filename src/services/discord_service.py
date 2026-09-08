# notifica alguem no discord com o resultado da analise de recarga.
#
# diferente do resto do projeto (que usa API sempre que da), aqui eu uso
# automacao de interface de proposito: a API de bot do Discord so consegue
# mandar DM pra quem tiver num servidor em comum com o bot, e a ideia aqui é
# só abrir o Discord (que a pessoa ja usa no dia a dia) e mandar mensagem
# pro privado de alguem especifico, sem precisar montar bot/servidor.
#
# como funciona: usa o atalho Ctrl+K do discord ("Ir para...") pra buscar o
# nome do contato e abrir a conversa - isso evita ficar clicando em posição
# fixa da lista de contatos, que muda de lugar toda hora.
#
# IMPORTANTE (aprendi isso testando): nunca digitar a mensagem sem antes
# CONFERIR que a conversa certa realmente abriu (via titulo da janela). Sem
# essa conferencia, um Enter que caiu cedo demais ja mandou a busca abrir a
# coisa errada e a automacao simplesmente digitou a mensagem la, sem
# perceber. Por isso tem retry: se nao confirmar que abriu certo, tenta de
# novo (Escape + busca de novo) antes de desistir.
#
# LINUX vs WINDOWS: a ferramenta que "aperta tecla" e "acha janela" é
# diferente em cada sistema. No Linux uso `xdotool`/`wmctrl` (binarios de
# sistema - testei o `pyautogui` primeiro mas ele nao conseguia se
# autenticar no X11 no meu ambiente). No Windows uso `pyautogui` (que la
# funciona direitinho, sem esse problema de autenticacao) + `pygetwindow`
# pra achar/focar a janela. A logica de "abrir busca, digitar, conferir
# titulo, enviar" é a mesma nos dois - só a parte de baixo nivel muda.
#
# obs: eu só tenho Linux pra testar. A parte Windows segue a documentacao
# oficial das bibliotecas, mas nao rodei de verdade num Windows - se algo
# nao funcionar exatamente igual, é o primeiro lugar pra olhar.

import platform
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

from src.config import settings
from src.utils.exceptions import NotificacaoDiscordError

SISTEMA = platform.system()  # "Linux", "Windows" ou "Darwin"


# ---------------------------------------------------------------------------
# checagens e utilitarios que nao dependem de sistema operacional
# ---------------------------------------------------------------------------

def _ascii_seguro(texto: str) -> str:
    """tira acento (é->e, ç->c, ã->a...) e troca traço especial por hifen
    normal antes de digitar.

    motivo: caractere fora do teclado padrao (acento, travessão "—" etc)
    pode obrigar a ferramenta de automacao a remapear uma tecla na hora pra
    "digitar" ele, e isso as vezes falha e o caractere simplesmente some -
    ja vi isso acontecer no Linux com "í" e depois com "—". Prefiro perder a
    acentuação (só na mensagem do Discord - o relatório .txt continua
    normal) do que arriscar a mensagem sair incompleta/errada."""
    texto = texto.replace("—", "-").replace("–", "-")
    sem_acento = unicodedata.normalize("NFKD", texto)
    return sem_acento.encode("ascii", "ignore").decode("ascii")


def montar_mensagem(analise: dict) -> str:
    """resumo curto pro discord - o relatorio completo fica no arquivo .txt,
    aqui e so o essencial pra pessoa do PIX decidir rapido."""
    if not analise["precisam_recarga"]:
        return "Não tem número pendente de recarga hoje."

    total = len(analise["precisam_recarga"])
    valor = f"R$ {analise['valor_total']:.2f}".replace(".", ",")

    linhas = [f"{total} chip(s) precisam de recarga - valor total {valor}", ""]
    for chip in analise["precisam_recarga"]:
        tag = " [URGENTE]" if chip["urgente"] else ""
        uso = chip.get("uso") or "(uso não informado)"
        linhas.append(f"- {chip['numero']}: {uso}{tag}")

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# backend LINUX (xdotool + wmctrl)
# ---------------------------------------------------------------------------

def _linux_verificar_ferramentas():
    faltando = [cmd for cmd in ("wmctrl", "xdotool") if shutil.which(cmd) is None]
    if faltando:
        raise NotificacaoDiscordError(
            f"ferramenta(s) ausente(s): {', '.join(faltando)}. "
            f"instale com: sudo apt install {' '.join(faltando)}"
        )


def _linux_discord_instalado() -> bool:
    if shutil.which("discord"):  # instalação via .deb/pacote nativo
        return True
    resultado = subprocess.run(
        ["flatpak", "info", settings.DISCORD_APP_ID], capture_output=True, text=True
    )
    return resultado.returncode == 0


def _linux_titulo_janela_discord() -> str:
    resultado = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
    for linha in resultado.stdout.splitlines():
        partes = linha.split(None, 3)
        if len(partes) == 4 and "Discord" in partes[3]:
            return partes[3]
    return ""


def _linux_discord_esta_rodando() -> bool:
    return bool(_linux_titulo_janela_discord())


def _linux_abrir_discord():
    if shutil.which("discord"):
        subprocess.Popen(["discord"])
        return
    # --ozone-platform=x11 e essencial aqui: por padrao o Discord (electron)
    # roda com renderizacao nativa wayland, e nesse modo a janela fica
    # invisivel pro wmctrl/xdotool (que so enxergam janelas X11/XWayland).
    subprocess.Popen(["flatpak", "run", settings.DISCORD_APP_ID, "--ozone-platform=x11"])


def _linux_focar_janela_discord():
    resultado = subprocess.run(["wmctrl", "-a", "Discord"], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise NotificacaoDiscordError(
            "nao consegui focar a janela do Discord. confere se ele realmente esta aberto."
        )


def _linux_teclar(tecla: str):
    resultado = subprocess.run(
        ["xdotool", "key", "--clearmodifiers", tecla], capture_output=True, text=True
    )
    if resultado.returncode != 0:
        raise NotificacaoDiscordError(f"xdotool falhou ao simular a tecla '{tecla}': {resultado.stderr}")


def _linux_digitar(texto: str):
    if not texto:
        return
    texto = _ascii_seguro(texto)
    # o "--" é necessário pq texto comecando com "-" (ex: "- 189... : Suporte")
    # senao o xdotool tenta interpretar como se fosse uma opção de linha de comando
    resultado = subprocess.run(
        [
            "xdotool", "type", "--clearmodifiers",
            "--delay", str(settings.DISCORD_DELAY_DIGITACAO_MS),
            "--", texto,
        ],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise NotificacaoDiscordError(f"xdotool falhou ao digitar texto: {resultado.stderr}")


# mapeia as "teclas logicas" que o resto do arquivo usa pro formato que o
# xdotool espera
_LINUX_TECLAS = {
    "busca": "ctrl+k",
    "confirmar": "Return",
    "cancelar": "Escape",
    "quebrar_linha": "shift+Return",
}


# ---------------------------------------------------------------------------
# backend WINDOWS (pyautogui + pygetwindow)
# ---------------------------------------------------------------------------

def _windows_verificar_ferramentas():
    faltando = []
    for pacote in ("pyautogui", "pygetwindow"):
        try:
            __import__(pacote)
        except ImportError:
            faltando.append(pacote)
    if faltando:
        raise NotificacaoDiscordError(
            f"biblioteca(s) ausente(s): {', '.join(faltando)}. "
            f"instale com: pip install {' '.join(faltando)}"
        )


def _windows_caminho_discord() -> Path | None:
    import os

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if not localappdata:
        return None
    caminho = Path(localappdata) / "Discord" / "Update.exe"
    return caminho if caminho.exists() else None


def _windows_discord_instalado() -> bool:
    return _windows_caminho_discord() is not None


def _windows_titulo_janela_discord() -> str:
    import pygetwindow as gw

    for titulo in gw.getAllTitles():
        if "Discord" in titulo:
            return titulo
    return ""


def _windows_discord_esta_rodando() -> bool:
    return bool(_windows_titulo_janela_discord())


def _windows_abrir_discord():
    caminho = _windows_caminho_discord()
    if not caminho:
        raise NotificacaoDiscordError(
            "nao encontrei o Discord instalado em %LOCALAPPDATA%\\Discord. "
            "confere se ele esta instalado (baixe em discord.com/download)."
        )
    subprocess.Popen([str(caminho), "--processStart", "Discord.exe"])


def _windows_focar_janela_discord():
    import pygetwindow as gw

    janelas = [w for w in gw.getWindowsWithTitle("Discord") if "Discord" in w.title]
    if not janelas:
        raise NotificacaoDiscordError("nao encontrei a janela do Discord pra focar.")

    janela = janelas[0]
    try:
        if janela.isMinimized:
            janela.restore()
        janela.activate()
    except Exception as e:
        raise NotificacaoDiscordError(f"nao consegui focar a janela do Discord: {e}")


def _windows_teclar(teclas: tuple):
    import pyautogui

    if len(teclas) == 1:
        pyautogui.press(teclas[0])
    else:
        pyautogui.hotkey(*teclas)


def _windows_digitar(texto: str):
    import pyautogui

    if not texto:
        return
    texto = _ascii_seguro(texto)
    pyautogui.write(texto, interval=settings.DISCORD_DELAY_DIGITACAO_MS / 1000)


# mesma ideia do _LINUX_TECLAS, mas no formato que o pyautogui espera
# (tupla de teclas pra apertar juntas, tipo hotkey)
_WINDOWS_TECLAS = {
    "busca": ("ctrl", "k"),
    "confirmar": ("enter",),
    "cancelar": ("esc",),
    "quebrar_linha": ("shift", "enter"),
}


# ---------------------------------------------------------------------------
# camada comum - dispatcha pro backend certo dependendo do SISTEMA
# ---------------------------------------------------------------------------

def _verificar_ferramentas():
    if SISTEMA == "Windows":
        _windows_verificar_ferramentas()
    elif SISTEMA == "Linux":
        _linux_verificar_ferramentas()
    else:
        raise NotificacaoDiscordError(
            f"notificacao no discord nao tem suporte pro sistema '{SISTEMA}' ainda "
            "(só Linux e Windows por enquanto)."
        )


def verificar_discord_instalado():
    """confere se o Discord parece estar instalado nessa maquina, ANTES de
    tentar abrir ou focar qualquer coisa. da um erro bem mais claro do que
    deixar o resto do fluxo falhar tentando abrir um app que nao existe."""
    if SISTEMA == "Windows":
        instalado = _windows_discord_instalado()
    else:
        instalado = _linux_discord_instalado()

    if not instalado:
        raise NotificacaoDiscordError(
            "o Discord nao parece estar instalado nessa maquina. "
            "baixe em https://discord.com/download e tente de novo."
        )


def _discord_esta_rodando() -> bool:
    if SISTEMA == "Windows":
        return _windows_discord_esta_rodando()
    return _linux_discord_esta_rodando()


def _titulo_janela_discord() -> str:
    if SISTEMA == "Windows":
        return _windows_titulo_janela_discord()
    return _linux_titulo_janela_discord()


def _esperar_janela_discord(timeout: float) -> bool:
    """fica checando se a janela do discord ja apareceu, de 1 em 1 segundo,
    em vez de um sleep fixo - inicializacao a frio as vezes demora bem mais
    que o esperado, e um sleep fixo curto demais deixa a automacao tentando
    mexer numa janela que ainda nem existe."""
    decorrido = 0.0
    intervalo = 1.0
    while decorrido < timeout:
        if _discord_esta_rodando():
            return True
        time.sleep(intervalo)
        decorrido += intervalo
    return False


def _abrir_discord_se_precisar():
    if _discord_esta_rodando():
        return

    if SISTEMA == "Windows":
        _windows_abrir_discord()
    else:
        _linux_abrir_discord()

    if not _esperar_janela_discord(settings.DISCORD_ESPERA_ABRIR_APP):
        raise NotificacaoDiscordError(
            f"o Discord nao terminou de abrir depois de {settings.DISCORD_ESPERA_ABRIR_APP}s. "
            "tenta rodar de novo (ou deixa o Discord ja aberto antes de rodar a automacao)."
        )


def _focar_janela_discord():
    if SISTEMA == "Windows":
        _windows_focar_janela_discord()
    else:
        _linux_focar_janela_discord()
    time.sleep(settings.DISCORD_ESPERA_FOCO)


def _teclar(nome_logico: str):
    if SISTEMA == "Windows":
        _windows_teclar(_WINDOWS_TECLAS[nome_logico])
    else:
        _linux_teclar(_LINUX_TECLAS[nome_logico])


def _digitar(texto: str):
    if SISTEMA == "Windows":
        _windows_digitar(texto)
    else:
        _linux_digitar(texto)


def _digitar_mensagem_multilinha(mensagem: str):
    """digita linha por linha quebrando com Shift+Enter - um Enter sozinho
    no campo de mensagem do Discord ENVIA a mensagem na hora."""
    linhas = mensagem.split("\n")
    for i, linha in enumerate(linhas):
        _digitar(linha)
        if i < len(linhas) - 1:
            _teclar("quebrar_linha")


def _conversa_correta_aberta(contato: str) -> bool:
    """confere se o titulo da janela bate com o contato esperado. o discord
    costuma mostrar o titulo tipo '@FrosT - Discord', entao comparo de
    forma tolerante (sem diferenciar maiusc/minusc, ignorando o @)."""
    titulo = _titulo_janela_discord().lower()
    alvo = contato.lower().lstrip("@").strip()
    return bool(alvo) and alvo in titulo


def _abrir_conversa_com_contato(contato: str):
    """abre a DM do contato via Ctrl+K, com retry: se depois de abrir o
    titulo da janela nao bater com o contato esperado, tenta de novo do
    zero (Escape pra fechar qualquer coisa que tenha ficado no ar + busca
    de novo) em vez de seguir digitando em cima de algo que pode estar
    errado."""
    for _tentativa in range(1, settings.DISCORD_MAX_TENTATIVAS_ABRIR_CONVERSA + 1):
        _teclar("cancelar")  # fecha qualquer busca/modal que tenha ficado aberto de antes
        time.sleep(0.5)

        _teclar("busca")
        time.sleep(settings.DISCORD_ESPERA_ABRIR_BUSCA)

        _digitar(contato)
        time.sleep(settings.DISCORD_ESPERA_FILTRAR_BUSCA)

        _teclar("confirmar")
        time.sleep(settings.DISCORD_ESPERA_ABRIR_CONVERSA)

        if _conversa_correta_aberta(contato):
            return

        time.sleep(settings.DISCORD_ESPERA_ENTRE_TENTATIVAS)

    raise NotificacaoDiscordError(
        f"depois de {settings.DISCORD_MAX_TENTATIVAS_ABRIR_CONVERSA} tentativa(s), nao consegui "
        f"confirmar que a conversa com '{contato}' abriu (titulo da janela ficou "
        f"'{_titulo_janela_discord()}'). abortando ANTES de digitar a mensagem, pra nao "
        "correr o risco de mandar pro lugar errado."
    )


def enviar_mensagem_discord(mensagem: str, contato: str | None = None) -> None:
    """abre o discord, confirma que a conversa certa abriu e so entao envia
    a mensagem. lanca NotificacaoDiscordError se algo no caminho falhar -
    inclusive se nao conseguir CONFIRMAR que abriu a conversa certa (nesse
    caso a mensagem nunca chega a ser digitada)."""
    _verificar_ferramentas()
    verificar_discord_instalado()

    contato = contato or settings.DISCORD_CONTATO_NOME
    if not contato:
        raise NotificacaoDiscordError("DISCORD_CONTATO_NOME nao configurado no .env")

    _abrir_discord_se_precisar()
    _focar_janela_discord()

    _abrir_conversa_com_contato(contato)

    _digitar_mensagem_multilinha(mensagem)
    _teclar("confirmar")  # esse enter final e que envia de verdade
