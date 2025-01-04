# main.py

"""
Script principal para iniciar el scraping. 
Se ejecuta desde la línea de comandos.
"""

import sys
import logging

from scraper.core import WebScraper
from scraper.utils import get_logger

logger = get_logger("Main")


def main():
    """
    Punto de entrada principal: 
    - Lee argumentos de la línea de comandos (URL, max_depth).
    - Ejecuta el scraper y guarda los resultados.
    """
    if len(sys.argv) < 2:
        print("Uso: python main.py <url> [max_depth=1]")
        sys.exit(1)

    website_url = sys.argv[1]
    max_depth = 1
    if len(sys.argv) >= 3:
        try:
            max_depth = int(sys.argv[2])
        except ValueError:
            max_depth = 1

    logger.info(f"Scraping la URL: {website_url} con max_depth={max_depth}")

    scraper = WebScraper(
        base_url=website_url,
        max_depth=max_depth,
        timeout=10,
        sleep_time=5,
        scrolldown=2
    )
    scraper.scrape()
    scraper.save_to_json()


if __name__ == "__main__":
    main()
