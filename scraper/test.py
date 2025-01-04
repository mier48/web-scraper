from requests_html import HTMLSession
import time

url = "https://beanywoodcafe.com/"

session = HTMLSession()
r = session.get(url)

# Prueba varios valores de sleep; a veces con 3-4 s no basta:
r.html.render(sleep=8, scrolldown=2, timeout=60)

rendered_html = r.html.html

# Guarda el HTML en un archivo temporal para ver si se han cargado los productos
with open("beanywood_rendered.html", "w", encoding="utf-8") as f:
    f.write(rendered_html)

print("HTML Renderizado guardado. Revisa 'beanywood_rendered.html' para comprobar si están los productos.")
