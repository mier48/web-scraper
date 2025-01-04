"""
Módulo de análisis de páginas web:
- IDs repetidos
- Falta / exceso de H1
- Falta de metadatos básicos
- Mismatch de enlaces de redes sociales (texto o iconos)
- Detección de la plataforma/CMS (WordPress, Shopify, etc.)
"""

from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import re
import requests

def analyze_page(soup: BeautifulSoup, page_data: Dict, base_url: str = None) -> Dict:
    """
    Lógica de análisis que consolida distintas revisiones:
    1. IDs repetidos.
    2. H1 checks (faltan / sobran).
    3. Meta description.
    4. Mismatched links (texto e iconos).
    5. CMS / plataforma detectada.

    :param soup: Objeto BeautifulSoup con el DOM.
    :param page_data: Diccionario con el contenido extraído (headings, meta_tags, etc.)
    :return: Un diccionario con los hallazgos en cada sección.
    """
    analysis_report = {}

    # --- 1. IDs repetidos ---
    repeated_ids = check_repeated_ids(soup)
    if repeated_ids:
        analysis_report["repeated_ids"] = repeated_ids

    # --- 2. H1 checks ---
    missing_h1, multiple_h1 = check_h1_issues(page_data)
    if missing_h1:
        analysis_report["missing_h1"] = True
    if multiple_h1 > 1:
        analysis_report["multiple_h1"] = multiple_h1

    # --- 3. Falta meta description ---
    if is_meta_description_missing(page_data):
        analysis_report["missing_meta_description"] = True

    # --- 4. Enlaces “mismatch” (texto e iconos) ---
    mismatched_links = find_mismatched_social_links(soup)
    if mismatched_links:
        analysis_report["mismatched_links"] = mismatched_links

    # --- 5. Detección de CMS / plataforma ---
    cms_detected = detect_cms_platform(soup, base_url=base_url)
    analysis_report["cms_platform"] = cms_detected

    return analysis_report

# ---------------------------------------------------------------------------
# SUB-FUNCIONES DE ANÁLISIS
# ---------------------------------------------------------------------------

def check_repeated_ids(soup: BeautifulSoup) -> List[str]:
    """
    Devuelve la lista de IDs que aparecen más de una vez en el DOM.
    """
    ids_count = {}
    for element in soup.find_all(attrs={"id": True}):
        el_id = element['id']
        ids_count[el_id] = ids_count.get(el_id, 0) + 1

    # IDs que se repiten
    repeated = [id_ for id_, count in ids_count.items() if count > 1]
    return repeated

def check_h1_issues(page_data: Dict) -> (bool, int):
    """
    Revisa si falta el H1 (missing_h1) o si hay más de uno (multiple_h1).
    :return: (missing_h1, multiple_h1_count)
    """
    h1_list = page_data.get("headings", {}).get("h1", [])
    missing_h1 = (len(h1_list) == 0)
    multiple_h1 = len(h1_list)  # si es >1, hay exceso
    return missing_h1, multiple_h1

def is_meta_description_missing(page_data: Dict) -> bool:
    """
    Verifica si falta la meta description en page_data["meta_tags"].
    """
    meta_tags = page_data.get("meta_tags", {})
    return not bool(meta_tags.get("description"))

def find_mismatched_social_links(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Busca enlaces que sugieren una red social (por texto o icono),
    pero apuntan a un dominio distinto.
    """
    mismatched_links = []

    # --- 1. Mismatch por texto ---
    text_based_social_keywords = {
        "instagram": "instagram.com",
        "tiktok": "tiktok.com",
        # Añade más si lo necesitas, ej. "facebook": "facebook.com", ...
    }

    # --- 2. Mismatch por icono (FontAwesome) ---
    icon_domain_map = {
        "fa-instagram": "instagram.com",
        "fa-tiktok": "tiktok.com",
    }

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        link_text = a_tag.get_text(strip=True).lower()

        # 1A) Check por texto visible
        for social_name, domain_snippet in text_based_social_keywords.items():
            if social_name in link_text and domain_snippet not in href:
                mismatched_links.append({
                    "text": link_text,
                    "href": href,
                    "expected_domain": domain_snippet,
                    "reason": f"Texto sugiere {social_name}, enlace no contiene {domain_snippet}"
                })

        # 1B) Check por iconos (ej. <i class="fab fa-instagram">)
        icon_tags = a_tag.find_all("i", class_=True)
        for icon_tag in icon_tags:
            icon_classes = icon_tag.get("class", [])
            for iclass in icon_classes:
                if iclass in icon_domain_map:
                    expected_domain = icon_domain_map[iclass]
                    if expected_domain not in href:
                        mismatched_links.append({
                            "icon_class": iclass,
                            "href": href,
                            "expected_domain": expected_domain,
                            "reason": f"Icono '{iclass}' sugiere {expected_domain}, pero el enlace no lo contiene"
                        })

    return mismatched_links

def detect_cms_platform(soup: BeautifulSoup, base_url: Optional[str] = None) -> List[str]:
    """
    Extrae pistas para detectar la plataforma o CMS usado (WordPress, Shopify, PrestaShop, Joomla, Drupal, etc.)
    y también intenta adivinar si está hecho con Ruby, Python, JSP, PHP...
    
    Adicionalmente, si 'base_url' está definido, lanzará una prueba a una URL inexistente 
    para ver si la página de error 404 delata un framework (p. ej. 'rails-default-error-page').
    
    Retorna una lista con todas las coincidencias encontradas (o ["Unknown"] si no se halla nada).
    """
    # 1) Convertimos HTML a minúsculas para buscar cadenas
    html_str = soup.prettify().lower()

    cms_platforms = set()

    # --------------------------------------
    # A) Revisión de <meta name="generator">
    # --------------------------------------
    generator_meta = soup.find("meta", attrs={"name": "generator"})
    if generator_meta and generator_meta.get("content"):
        gen_content = generator_meta["content"].lower()

        if "wordpress" in gen_content:
            cms_platforms.add("WordPress")
        if "shopify" in gen_content:
            cms_platforms.add("Shopify")
        if "joomla" in gen_content:
            cms_platforms.add("Joomla")
        if "drupal" in gen_content:
            cms_platforms.add("Drupal")
        if "prestashop" in gen_content:
            cms_platforms.add("PrestaShop")
        if "squarespace" in gen_content:
            cms_platforms.add("Squarespace")
        if "wix.com" in gen_content:
            cms_platforms.add("Wix")
        # añade más si lo deseas

    # ------------------------------------
    # B) Indicios por rutas/carpetas/strings (CMS)
    # ------------------------------------
    if "wp-content" in html_str or "wp-includes" in html_str:
        cms_platforms.add("WordPress")
    if "woocommerce" in html_str:
        cms_platforms.add("WooCommerce (WP)")
    if "elementor" in html_str:
        cms_platforms.add("WordPress + Elementor")

    if "cdn.shopify.com" in html_str or "powered by shopify" in html_str:
        cms_platforms.add("Shopify")

    if "powered by joomla" in html_str or "index.php?option=com_" in html_str:
        cms_platforms.add("Joomla")

    if "sites/default/files" in html_str or "powered by drupal" in html_str:
        cms_platforms.add("Drupal")

    if "powered by prestashop" in html_str or "modules/prestashop" in html_str:
        cms_platforms.add("PrestaShop")

    if "static1.squarespace.com" in html_str or "powered by squarespace" in html_str:
        cms_platforms.add("Squarespace")

    if "wix-code" in html_str or "powered by wix" in html_str:
        cms_platforms.add("Wix")

    if "powered by weebly" in html_str or "weebly.com" in html_str:
        cms_platforms.add("Weebly")

    # ------------------------------------
    # C) Indicios de lenguaje / framework (HTML principal)
    # ------------------------------------
    # 1. Extensiones (php, jsp, rb, py, asp, aspx)
    pattern_ext = re.compile(r'\.(php|jsp|rb|py|asp|aspx)(\?|$|")')
    matches_ext = pattern_ext.findall(html_str)
    found_extensions = {m[0] for m in matches_ext}
    for ext in found_extensions:
        if ext == "php":
            cms_platforms.add("PHP")
        elif ext == "jsp":
            cms_platforms.add("Java/JSP")
        elif ext == "rb":
            cms_platforms.add("Ruby")
        elif ext == "py":
            cms_platforms.add("Python")
        elif ext in ("asp", "aspx"):
            cms_platforms.add(".NET (ASP)")

    # 2. Palabras clave de frameworks
    frameworks_map = {
        "rails": "Ruby on Rails",
        "sinatra": "Ruby (Sinatra)",
        "django": "Python (Django)",
        "flask": "Python (Flask)",
        "pylons": "Python (Pylons)",
        "web2py": "Python (web2py)",
        "laravel": "PHP (Laravel)",
        "symfony": "PHP (Symfony)",
        "codeigniter": "PHP (CodeIgniter)",
        "cakephp": "PHP (CakePHP)",
        "phalcon": "PHP (Phalcon)",
        "fuelphp": "PHP (FuelPHP)",
    }
    for key, val in frameworks_map.items():
        if key in html_str:
            cms_platforms.add(val)

    # ------------------------------------
    # D) Si se proporciona base_url, probamos 404
    #    (páginas de error a menudo delatan frameworks, ej. Rails)
    # ------------------------------------
    if base_url:
        # Si no se ha detectado Ruby on Rails, o si el set está vacío, probamos la 404 detection
        if "Ruby on Rails" not in cms_platforms or not cms_platforms:
            possible_rails = try_404_detection(base_url)
            if possible_rails:  # Devuelve "Ruby on Rails" si lo detecta
                cms_platforms.add(possible_rails)

    # ------------------------------------
    # E) Devolvemos resultados
    # ------------------------------------
    return list(cms_platforms) if cms_platforms else ["Unknown"]

def try_404_detection(base_url: str, timeout: int = 5) -> Optional[str]:
    """
    Intenta forzar una página 404, 
    y revisa si el HTML resultante delata Ruby on Rails (o similar).
    
    :param base_url: URL base del sitio (sin trailing slash preferiblemente)
    :param timeout: Tiempo máximo de espera (s)
    :return: "Ruby on Rails" si detecta rails-default-error-page, o None si no se detecta nada
    """
    test_url = base_url.rstrip('/') + '/this_page_should_not_exist_404test'
    try:
        r = requests.get(test_url, timeout=timeout)
        if r.status_code == 404:
            # Analizar el cuerpo de la respuesta
            body_404 = r.text.lower()
            # Rails default error page
            if "rails-default-error-page" in body_404:
                return "Ruby on Rails"
            # Podrías buscar otras firmas...
        # Si no es 404, o no hay firma => None
    except requests.RequestException:
        pass

    return None