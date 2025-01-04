"""
Módulo principal del WebScraper, con la clase que realiza:
- BFS (requests_html)
- Extracción de datos
- Integración con la lógica de análisis
"""

import os
import re
import json
from typing import Tuple, List, Dict, Optional, Set
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from requests_html import HTMLSession
from bs4 import BeautifulSoup
from tqdm import tqdm

from .utils import get_logger
from .analysis import analyze_page

logger = get_logger(__name__)


class WebScraper:
    """
    Clase WebScraper que realiza un scraping BFS (Breadth-First Search) 
    partiendo de una URL base. Usa requests_html para renderizar 
    JavaScript básico.
    """
    def __init__(
        self,
        base_url: str,
        max_depth: int = 1,
        timeout: int = 10,
        sleep_time: int = 5,
        scrolldown: int = 2,
    ) -> None:
        """
        :param base_url: URL base que se desea scrapear.
        :param max_depth: Profundidad máxima de scraping (BFS).
        :param timeout: Tiempo máximo de espera para requests (segundos).
        :param sleep_time: Tiempo de espera tras renderizar con requests_html.
        :param scrolldown: Cantidad de 'scroll' a simular en render.
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.scrolldown = scrolldown

        # Estructuras internas
        self.visited_urls: Set[str] = set()
        self.data: Dict[str, Dict] = {}

        # Sesión para requests_html
        self.session = HTMLSession()

    def scrape(self) -> None:
        """
        Inicia el scraping BFS y va almacenando resultados en self.data
        """
        queue = deque([(self.base_url, 0)])

        # Progreso aproximado (no exacto). Ajusta según tus necesidades
        pbar = tqdm(total=100, desc="Scraping Progress (aprox)")

        while queue:
            url, depth = queue.popleft()
            if depth > self.max_depth:
                break

            if url not in self.visited_urls:
                self.visited_urls.add(url)
                page_data, links = self.scrape_page(url)
                if page_data:
                    self.data[url] = page_data

                # BFS: añade enlaces del mismo dominio
                for link_url in links:
                    if link_url not in self.visited_urls and self.is_same_domain(link_url):
                        queue.append((link_url, depth + 1))

            pbar.update(1)

        pbar.close()

    def scrape_page(self, url: str) -> Tuple[Optional[Dict], List[str]]:
        """
        Descarga + renderiza la página con requests_html, 
        extrae la info y devuelve (page_data, links).
        """
        try:
            logger.info(f"Scrapeando: {url}")
            r = self.session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=self.timeout)
            r.html.render(sleep=self.sleep_time, scrolldown=self.scrolldown, timeout=self.timeout)

            rendered_html = r.html.html
            soup = BeautifulSoup(rendered_html, 'html.parser')

            # Extraer contenido principal
            page_data = self.extract_content(soup, url)

            # Aplicar análisis
            analysis = analyze_page(soup, page_data, base_url=self.base_url)
            if analysis:
                page_data["analysis"] = analysis

            # Extraer enlaces
            links = {
                urljoin(url, link.get('href', ''))
                for link in soup.find_all('a', href=True)
            }
            return page_data, list(links)

        except (requests.exceptions.RequestException, Exception) as e:
            logger.error(f"Error scraping {url}: {e}")
            return None, []

    def extract_content(self, soup: BeautifulSoup, current_url: str) -> Dict:
        """
        Extrae:
        - Título y meta_tags
        - Encabezados
        - Texto (párrafos)
        - Imágenes
        - Emails
        - Productos (sección 'productos')
        - Secciones (IDs y clases)
        """
        title = soup.title.string.strip() if soup.title else ""

        # Metatags
        meta_tags = {}
        for meta in soup.find_all("meta"):
            if meta.get("name"):
                meta_tags[meta["name"].lower()] = meta.get("content", "")
            elif meta.get("property"):
                meta_tags[meta["property"].lower()] = meta.get("content", "")

        # Encabezados
        headers = {}
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            headers[level] = [h.get_text(strip=True) for h in soup.find_all(level)]

        # Párrafos
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
        full_text = "\n".join(paragraphs)

        # Imágenes
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            src = urljoin(current_url, src)
            images.append({"src": src, "alt": alt})

        # Emails
        email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        found_emails = re.findall(email_pattern, soup.get_text())
        unique_emails = list(set(found_emails))

        # Productos
        products = self.extract_products(soup, current_url)

        # Secciones
        sections_info = []
        for section in soup.find_all("section"):
            sec_id = section.get("id", "")
            sec_classes = section.get("class", [])
            if isinstance(sec_classes, list):
                sec_classes_str = " ".join(sec_classes)
            else:
                sec_classes_str = sec_classes if sec_classes else ""
            sections_info.append({"id": sec_id, "classes": sec_classes_str})

        # Formularios
        forms_info = []
        forms = soup.find_all("form")
        for form in forms:
            method = (form.get("method") or "").upper()  # GET, POST, etc.
            action = (form.get("action") or "").strip()

            # Recolectar info de los campos
            fields = []

            # <input>
            for inp in form.find_all("input"):
                field_type = inp.get("type", "text")  # Por defecto "text" si no está
                field_name = inp.get("name", "")
                fields.append({
                    "tag": "input",
                    "type": field_type,
                    "name": field_name
                })

            # <textarea>
            for txt in form.find_all("textarea"):
                field_name = txt.get("name", "")
                fields.append({
                    "tag": "textarea",
                    "name": field_name
                })

            # <select>
            for sel in form.find_all("select"):
                field_name = sel.get("name", "")
                options = [opt.get_text(strip=True) for opt in sel.find_all("option")]
                fields.append({
                    "tag": "select",
                    "name": field_name,
                    "options": options
                })

            forms_info.append({
                "method": method,
                "action": action,
                "fields": fields
            })

        content = {
            "url": current_url,
            "title": title,
            "meta_tags": meta_tags,
            "headings": headers,
            "text": full_text,
            "images": images,
            "emails": unique_emails,
            "products": products,
            "sections": sections_info,
            "forms": forms_info
        }

        return content

    def extract_products(self, soup: BeautifulSoup, current_url: str) -> List[Dict]:
        """
        Busca productos en:
        1) Estructura antigua con id="productos" (<div class="collection-item w-dyn-item">).
        2) Estructura Shopify con <div class="product-grid-item" data-product-id="...">.

        Retorna una lista con todos los productos encontrados (de ambas estructuras).
        """
        products = []

        # --------------------------------------------------
        # 1) Estructura antigua (id="productos")
        # --------------------------------------------------
        product_sections = soup.find_all("section", id="productos")
        for product_section in product_sections:
            product_items = product_section.select("div.collection-item.w-dyn-item")
            for item in product_items:
                link_block = item.select_one("a.link-block-12.normal.w-inline-block")
                if not link_block:
                    continue

                href = link_block.get("href", "")
                product_url = urljoin(current_url, href)

                title_el = link_block.select_one("h2.heading-2")
                product_name = title_el.get_text(strip=True) if title_el else "Sin título"

                price_el = link_block.select_one("h4.heading-3[data-commerce-type='variation-price']")
                product_price = price_el.get_text(strip=True) if price_el else "Sin precio"

                img_el = link_block.select_one("img.image-3")
                product_img_src = ""
                product_img_alt = ""
                if img_el:
                    product_img_src = urljoin(current_url, img_el.get("src", ""))
                    product_img_alt = img_el.get("alt", "")

                products.append({
                    "name": product_name,
                    "url": product_url,
                    "price": product_price,
                    "image_src": product_img_src,
                    "image_alt": product_img_alt
                })

        # --------------------------------------------------
        # 2) Estructura Shopify (product-grid-item[data-product-id])
        # --------------------------------------------------
        shopify_cards = soup.select("div.product-grid-item[data-product-id]")
        for card in shopify_cards:
            # a) Enlace principal + nombre
            link_tag = card.select_one("a.product__media__holder[href]")
            if link_tag:
                product_href = link_tag.get("href", "")
                product_url = urljoin(current_url, product_href)
                product_name = link_tag.get("aria-label", "").strip()
            else:
                product_url = current_url
                product_name = ""

            # Como fallback, si el aria-label está vacío, buscamos el .product-grid-item__title
            if not product_name:
                title_tag = card.select_one("a.product-grid-item__title")
                if title_tag:
                    product_name = title_tag.get_text(strip=True)
            if not product_name:
                product_name = "Sin título"

            # b) Precio actual y precio anterior, si está en <a class="product-grid-item__price price">
            current_price = "Sin precio"
            old_price = ""
            price_link = card.select_one("a.product-grid-item__price.price")
            if price_link:
                # Ej.: "30,00€<s class="sale-price">40,00€</s>"
                text_all = price_link.get_text(strip=True)
                sale_el = price_link.select_one("s.sale-price")
                if sale_el:
                    old_price_text = sale_el.get_text(strip=True)
                    old_price = old_price_text
                    # El precio actual es el texto total menos la parte de <s>
                    current_price = text_all.replace(old_price_text, "").strip()
                else:
                    current_price = text_all

            # c) Imagen principal
            #    Observamos <div class="product__media product__media--featured" style="background-image: url(...)">
            image_src = ""
            media_div = card.select_one("div.product__media--featured")
            if media_div and media_div.has_attr("style"):
                style_str = media_div["style"]  # "background-image: url(...)"
                match = re.search(r'url\(([^)]+)\)', style_str)
                if match:
                    raw_url = match.group(1).strip('"').strip("'")
                    image_src = urljoin(current_url, raw_url)

            # Si no se encontró, probamos con data-bgset, tomando la última URL
            if not image_src and media_div and media_div.has_attr("data-bgset"):
                bgset_str = media_div["data-bgset"]
                candidates = [part.strip() for part in bgset_str.split(",")]
                if candidates:
                    # Tomamos la última (normalmente la de mayor resolución)
                    last_part = candidates[-1].strip()
                    # Ej: "//pbsapparel.com/... 899w 1348h"
                    splitted = last_part.split()
                    if splitted:
                        raw_url = splitted[0]  # primera parte antes de '899w'
                        image_src = urljoin(current_url, raw_url.lstrip("//"))

            # d) Añadir al listado final
            products.append({
                "name": product_name,
                "url": product_url,
                "price": current_price,
                "old_price": old_price,  # si no hay, queda vacío
                "image_src": image_src,
                "image_alt": ""  # no se detecta alt en este snippet, p.ej. lo dejamos vacío
            })

        return products

    def is_same_domain(self, url: str) -> bool:
        """
        Verifica si la URL está en el mismo dominio que self.base_url.
        """
        base_domain = urlparse(self.base_url).netloc.lower()
        current_domain = urlparse(url).netloc.lower()
        return base_domain == current_domain

    def save_to_json(self, file_name: Optional[str] = None) -> None:
        """
        Guarda self.data en un archivo JSON en la carpeta 'analysis_scraping'.
        """
        folder_name = "analysis_scraping"
        os.makedirs(folder_name, exist_ok=True)

        if not file_name:
            domain_name = urlparse(self.base_url).netloc.split(':')[0]
            domain_name = domain_name.replace("www.", "").split('.')[0]
            file_name = f"{domain_name}.json"

        file_path = os.path.join(folder_name, file_name)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            logger.info(f"Datos guardados en {file_path}")
        except OSError as err:
            logger.error(f"No se pudo guardar el archivo JSON: {err}")
