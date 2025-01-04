"""
Funciones utilitarias para el proyecto de scraping: 
logging, normalización de URLs, etc.
"""

import logging

def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    Crea y configura un logger con el nombre y nivel deseado.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        ch = logging.StreamHandler()
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        ch.setFormatter(fmt)
        logger.addHandler(ch)
    return logger
