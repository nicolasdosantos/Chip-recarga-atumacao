# notifica alguem no discord com o resultado da analise de recarga.
#
# diferente do resto do projeto (que usa API sempre que da), aqui eu uso
# automacao de interface de proposito: a API de bot do Discord so consegue
# mandar DM pra quem tiver num servidor em comum com o bot, e a ideia aqui é
# só abrir o Discord (que a pessoa ja usa no dia a dia) e mandar mensagem
# pro privado de alguem especifico, sem precisar montar bot/servidor.
#
# uso "xdotool" em vez de "pyautogui" pra simular teclado/foco de janela.
# testei os dois e o pyautogui (via python-xlib) nao conseguia se autenticar
# no X11 nesse ambiente, enquanto o xdotool (ferramenta nativa) funciona sem
# problema - entao ficou mais simples e mais leve ir direto de xdotool via
# subprocess, sem precisar de mais uma dependencia python.
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

import shutil
import subprocess
import time
import unicodedata

from src.config import settings
from src.utils.exceptions import NotificacaoDiscordError


def _verificar_ferramentas():
    faltando = [cmd for cmd in ("wmctrl", "xdotool") if shutil.which(cmd) is None]
    if faltando:
        raise NotificacaoDiscordError(
            f"ferramenta(s) ausente(s): {', '.join(faltando)}. "
            f"instale com: sudo apt install {' '.join(faltando)}"
        )


def _titulo_janela_discord() -> str:
    """devolve o titulo da janela do discord (ex: '@FrosT - Discord'), ou
    string vazia se a janela nao existir. uso isso tanto pra saber se o
    discord ta aberto quanto pra conferir QUAL conversa ta aberta."""
    resultado = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
    for linha in resultado.stdout.splitlines():
        partes = linha.split(None, 3)
        if len(partes) == 4 and "Discord" in partes[3]:
            return partes[3]
    return ""


def _discord_esta_rodando() -> bool:
    return bool(_titulo_janela_discord())


def _conversa_correta_aberta(contato: str) -> bool:
    """confere se o titulo da janela bate com o contato esperado. o discord
    costuma mostrar o titulo tipo '@FrosT - Discord', entao comparo de
    forma tolerante (sem diferenciar maiusc/minusc, ignorando o @)."""
    titulo = _titulo_janela_discord().lower()
    alvo = contato.lower().lstrip("@").strip()
    return bool(alvo) and alvo in titulo


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

    try:
        # --ozone-platform=x11 e essencial aqui: por padrao o Discord (electron)
        # roda com renderizacao nativa wayland, e nesse modo a janela fica
        # invisivel pro wmctrl/xdotool (que so enxergam janelas X11/XWayland).
        # forcando x11, a janela aparece normal pras ferramentas de automacao.
        subprocess.Popen(["flatpak", "run", settings.DISCORD_APP_ID, "--ozone-platform=x11"])
    except FileNotFoundError:
        raise NotificacaoDiscordError(
            "nao consegui abrir o Discord (comando 'flatpak' nao encontrado). "
            "confere se o Discord ta instalado."
        )

    if not _esperar_janela_discord(settings.DISCORD_ESPERA_ABRIR_APP):
        raise NotificacaoDiscordError(
            f"o Discord nao terminou de abrir depois de {settings.DISCORD_ESPERA_ABRIR_APP}s. "
            "tenta rodar de novo (ou deixa o Discord ja aberto antes de rodar a automacao)."
        )


def _focar_janela_discord():
    resultado = subprocess.run(["wmctrl", "-a", "Discord"], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise NotificacaoDiscordError(
            "nao consegui focar a janela do Discord. confere se ele realmente esta aberto."
        )
    time.sleep(settings.DISCORD_ESPERA_FOCO)


def _ascii_seguro(texto: str) -> str:
    """tira acento (é->e, ç->c, ã->a...) e troca traço especial por hifen
    normal antes de mandar pro xdotool.

    motivo: caractere fora do teclado padrao (acento, travessão "—" etc)
    obriga o xdotool a remapear uma tecla na hora pra "digitar" ele, e isso
    as vezes falha e o caractere simplesmente some da mensagem - ja vi isso
    acontecer com "í" e depois com "—", em digitações diferentes. Prefiro
    perder a acentuação do que arriscar a mensagem sair incompleta/errada."""
    texto = texto.replace("—", "-").replace("–", "-")
    sem_acento = unicodedata.normalize("NFKD", texto)
    return sem_acento.encode("ascii", "ignore").decode("ascii")


def _teclar(tecla: str):
    resultado = subprocess.run(
        ["xdotool", "key", "--clearmodifiers", tecla], capture_output=True, text=True
    )
    if resultado.returncode != 0:
        raise NotificacaoDiscordError(f"xdotool falhou ao simular a tecla '{tecla}': {resultado.stderr}")


def _digitar(texto: str):
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


def _digitar_mensagem_multilinha(mensagem: str):
    """digita linha por linha usando Shift+Enter pra quebrar linha - um Enter
    sozinho no campo de mensagem do Discord ENVIA a mensagem na hora."""
    linhas = mensagem.split("\n")
    for i, linha in enumerate(linhas):
        _digitar(linha)
        if i < len(linhas) - 1:
            _teclar("shift+Return")


def _abrir_conversa_com_contato(contato: str):
    """abre a DM do contato via Ctrl+K, com retry: se depois de abrir o
    titulo da janela nao bater com o contato esperado, tenta de novo do
    zero (Escape pra fechar qualquer coisa que tenha ficado no ar + busca
    de novo) em vez de seguir digitando em cima de algo que pode estar
    errado."""
    for tentativa in range(1, settings.DISCORD_MAX_TENTATIVAS_ABRIR_CONVERSA + 1):
        _teclar("Escape")  # fecha qualquer busca/modal que tenha ficado aberto de antes
        time.sleep(0.5)

        _teclar("ctrl+k")
        time.sleep(settings.DISCORD_ESPERA_ABRIR_BUSCA)

        _digitar(contato)
        time.sleep(settings.DISCORD_ESPERA_FILTRAR_BUSCA)

        _teclar("Return")
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

    contato = contato or settings.DISCORD_CONTATO_NOME
    if not contato:
        raise NotificacaoDiscordError("DISCORD_CONTATO_NOME nao configurado no .env")

    _abrir_discord_se_precisar()
    _focar_janela_discord()

    _abrir_conversa_com_contato(contato)

    _digitar_mensagem_multilinha(mensagem)
    _teclar("Return")  # esse enter final e que envia de verdade


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
