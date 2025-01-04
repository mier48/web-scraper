import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import re
import json
from collections import deque
from tqdm import tqdm
from requests_html import HTMLSession
from bs4 import BeautifulSoup

class WebScraper:
    def __init__(self, base_url, max_depth=1, timeout=10):
        """
        :param base_url: URL base que se desea scrapear.
        :param max_depth: Profundidad máxima de scraping (BFS).
        :param timeout: Tiempo máximo de espera en requests (segundos).
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.timeout = timeout
        self.visited_urls = set()
        self.data = {}
        self.session = HTMLSession()

    def scrape(self):
        """
        Inicia el proceso de scraping utilizando BFS 
        hasta la profundidad configurada.
        """
        # Cola para BFS: cada elemento es (url, depth)
        queue = deque([(self.base_url, 0)])

        # Progreso total aproximado (puede variar en tiempo de ejecución)
        # Asumiendo un máximo estimado para la barra de progreso
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

                # Agregar los enlaces al BFS si están en el mismo dominio y no sobrepasa la profundidad
                for link_url in links:
                    if link_url not in self.visited_urls and self.is_same_domain(link_url):
                        queue.append((link_url, depth + 1))

            pbar.update(1)
        pbar.close()

    def scrape_page(self, url):
        """
        Extrae toda la información de la página, devolviendo:
        - page_data: diccionario con datos relevantes de la página
        - links: enlaces extraídos de la página
        """
        try:
            # 1. Petición inicial con requests_html
            r = self.session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=self.timeout)

            # 2. Renderizamos JS para que aparezcan los productos dinámicos
            #    Ajusta sleep si la web tarda más de lo esperado (p.ej., 5, 8, 10)
            r.html.render(sleep=1, scrolldown=2, timeout=self.timeout)

            # 3. Obtenemos el HTML final (con JavaScript ejecutado) y lo parseamos
            rendered_html = r.html.html
            soup = BeautifulSoup(rendered_html, 'html.parser')

            # 4. Extraer datos de la página
            page_data = self.extract_content(soup, url)

            # 5. Extraer todos los enlaces (ya renderizados)
            links = {
                urljoin(url, link.get('href'))
                for link in soup.find_all('a', href=True)
            }

            return page_data, links

        except (requests.exceptions.RequestException, Exception) as e:
            print(f"Error scraping {url}: {e}")
            return None, []

    def extract_content(self, soup, current_url):
        """
        Extrae:
        - Título de la página
        - Metatags
        - Encabezados
        - Texto
        - Imágenes
        - Emails (si existen)
        - Productos en la sección "productos" (si existen)
        - Lista de secciones con sus IDs y clases
        """

        # ----------------------
        # 1. Título de la página
        # ----------------------
        title = soup.title.string.strip() if soup.title else ""

        # ----------------------
        # 2. Metatags
        # ----------------------
        meta_tags = {}
        for meta in soup.find_all("meta"):
            if meta.get("name"):
                meta_tags[meta["name"].lower()] = meta.get("content", "")
            elif meta.get("property"):
                meta_tags[meta["property"].lower()] = meta.get("content", "")

        # ----------------------
        # 3. Encabezados
        # ----------------------
        headers = {}
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            headers[level] = [h.get_text(strip=True) for h in soup.find_all(level)]

        # ----------------------
        # 4. Texto (párrafos)
        # ----------------------
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
        full_text = "\n".join(paragraphs)

        # ----------------------
        # 5. Imágenes
        # ----------------------
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            src = urljoin(current_url, src)
            images.append({"src": src, "alt": alt})

        # ----------------------
        # 6. Emails en el texto
        # ----------------------
        email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        all_text = soup.get_text()  
        found_emails = re.findall(email_pattern, all_text)
        unique_emails = list(set(found_emails))

        # ----------------------
        # 7. Productos
        # ----------------------
        products = self.extract_products(soup, current_url)

        # 8. Secciones (IDs y clases)
        sections_info = []
        for section in soup.find_all("section"):
            sec_id = section.get("id", "")
            # A veces 'class' viene en forma de lista, la convertimos a string con espacios
            sec_classes = " ".join(section.get("class", []))
            sections_info.append({"id": sec_id, "classes": sec_classes})

        # 9. Estructura final
        content = {
            "url": current_url,
            "title": title,
            "meta_tags": meta_tags,
            "headings": headers,
            "text": full_text,
            "images": images,
            "emails": unique_emails,
            "products": products,
            "sections": sections_info
        }

        return content
    
    def extract_products(self, soup, current_url):
        """
        Busca todas las secciones con id="productos" y extrae los productos
        definidos como <div class="collection-item w-dyn-item">.
        """
        product_sections = soup.find_all("section", id="productos")
        products = []

        for product_section in product_sections:
            # Cada producto está en div.collection-item
            product_items = product_section.select("div.collection-item.w-dyn-item")
            for item in product_items:
                # Enlace y contenedor principal
                link_block = item.select_one("a.link-block-12.normal.w-inline-block")
                if not link_block:
                    continue

                # Enlace del producto
                href = link_block.get("href", "")
                product_url = urljoin(current_url, href)

                # Nombre del producto
                title_el = link_block.select_one("h2.heading-2")
                product_name = title_el.get_text(strip=True) if title_el else "Sin título"

                # Precio (dentro de un <h4 class="heading-3" data-commerce-type="variation-price">)
                price_el = link_block.select_one("h4.heading-3[data-commerce-type='variation-price']")
                product_price = price_el.get_text(strip=True) if price_el else "Sin precio"

                # Imagen principal
                img_el = link_block.select_one("img.image-3")
                product_img_src = ""
                product_img_alt = ""
                if img_el:
                    product_img_src = urljoin(current_url, img_el.get("src", ""))
                    product_img_alt = img_el.get("alt", "")

                # Guardamos el producto en la lista
                products.append({
                    "name": product_name,
                    "url": product_url,
                    "price": product_price,
                    "image_src": product_img_src,
                    "image_alt": product_img_alt
                })

        return products

    def is_same_domain(self, url):
        """
        Verifica si una URL está dentro del mismo dominio (host) que la base.
        """
        base_domain = urlparse(self.base_url).netloc
        current_domain = urlparse(url).netloc
        return base_domain == current_domain

    def save_to_json(self, file_name=None):
        """
        Guarda el contenido scrapreado en un archivo JSON.
        Si no se especifica nombre de archivo, se genera uno por defecto
        basado en el dominio base.
        """
        # 1. Nombre de la carpeta de destino
        folder_name = "analysis_scraping"
        os.makedirs(folder_name, exist_ok=True)  # Crea la carpeta si no existe

        if not file_name:
            domain_name = urlparse(self.base_url).netloc.split(':')[0]
            domain_name = domain_name.replace("www.", "").split('.')[0]
            file_name = f"{domain_name}.json"

        # 2. Construir la ruta completa del archivo
        file_path = os.path.join(folder_name, file_name)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

        print(f"Data saved to {file_path}")

if __name__ == "__main__":
    website_url = input("Enter the URL of the website to scrape: ").strip()
    max_depth_input = input("Enter maximum depth (default=1): ").strip()

    try:
        max_depth = int(max_depth_input)
    except ValueError:
        max_depth = 1

    scraper = WebScraper(base_url=website_url, max_depth=max_depth)
    scraper.scrape()
    scraper.save_to_json()
