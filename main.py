import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import json
from collections import deque
from tqdm import tqdm

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
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=self.timeout)
            if response.status_code != 200:
                return None, []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraer datos de la página
            page_data = self.extract_content(soup, url)

            # Extraer todos los enlaces
            links = {urljoin(url, link['href']) for link in soup.find_all('a', href=True)}

            return page_data, links

        except (requests.exceptions.RequestException, Exception) as e:
            # Podrías registrar errores, imprimirlos o manejarlos de otra forma
            print(f"Error scraping {url}: {e}")
            return None, []

    def extract_content(self, soup, current_url):
        """
        Extrae la información más relevante de un objeto BeautifulSoup:
        - Título
        - Meta tags (genéricos, Open Graph, Twitter Cards)
        - Encabezados (h1, h2, h3...)
        - Texto principal (p)
        - Imágenes (src, alt)
        - Scripts in-page, si interesa
        """
        # Título de la pestaña
        title = soup.title.string.strip() if soup.title else ""

        # Recoger meta tags
        meta_tags = {}
        for meta in soup.find_all("meta"):
            # 'name' o 'property' como clave, 'content' como valor
            if meta.get("name"):
                meta_tags[meta["name"].lower()] = meta.get("content", "")
            elif meta.get("property"):
                meta_tags[meta["property"].lower()] = meta.get("content", "")

        # Encabezados
        headers = {}
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            headers[level] = [
                h.get_text(strip=True) for h in soup.find_all(level)
            ]

        # Texto (párrafos)
        paragraphs = [
            p.get_text(strip=True) for p in soup.find_all('p')
            if p.get_text(strip=True)
        ]
        full_text = "\n".join(paragraphs)

        # Imágenes
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            # Unir URL relativo a la base del current_url
            src = urljoin(current_url, src)
            images.append({
                "src": src,
                "alt": alt
            })

        # Estructurar datos
        content = {
            "url": current_url,
            "title": title,
            "meta_tags": meta_tags,
            "headings": headers,
            "text": full_text,
            "images": images
        }
        return content

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
