# configuracao central de log. um arquivo novo por execucao (com timestamp
# no nome) + tambem mostra no console, assim da pra acompanhar rodando ao
# vivo e ainda ter o historico salvo depois.

import logging
from datetime import datetime

from src.config import settings

_logger = None  # cache - so monta o logger uma vez, mesmo se chamar get_logger() varias vezes


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("chip_recarga")
    logger.setLevel(logging.INFO)

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%d/%m/%Y %H:%M:%S"
    )

    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formato)
    logger.addHandler(handler_console)

    # o log em arquivo é "best effort": se por algum motivo nao der pra
    # criar a pasta/arquivo (permissao negada, disco cheio, etc), a
    # automacao ainda funciona normalmente só com log no console, em vez de
    # quebrar antes mesmo do main() rodar (isso acontece ANTES de qualquer
    # try/except do main.py, entao aqui é o unico lugar pra tratar isso).
    try:
        settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"automacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        caminho_log = settings.LOGS_DIR / nome_arquivo

        handler_arquivo = logging.FileHandler(caminho_log, encoding="utf-8")
        handler_arquivo.setFormatter(formato)
        logger.addHandler(handler_arquivo)
    except OSError as e:
        logger.warning(f"nao consegui criar o log em arquivo ({e}) - seguindo só com log no console")

    _logger = logger
    return logger
