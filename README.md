# Web Scraping Project

[![Version: 1.0.0](https://img.shields.io/badge/Version-1.0.0-blue.svg)](./README.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

This project implements a web scraper using Python. The scraper performs exploration (BFS) and analysis of web pages, extracting structured data and generating reports.

---

## Requirements

Before running the project, ensure you have the following requirements installed:

### Python

- Version: **Python 3.8 or higher**

### Dependencies

Install the necessary dependencies by running:

```
$ pip install -r requirements.txt
```

- **requests-html**: For making HTTP requests and rendering basic JavaScript.
- **BeautifulSoup4**: For parsing the DOM of web pages.
- **tqdm**: For displaying progress during scraping.

---

## Project Structure

```text
.
├── main.py                 # Main script to run the scraper.
├── scraper/
│   ├── __init__.py
│   ├── core.py            # Main scraping logic.
│   ├── analysis.py        # Web page analysis module.
│   └── utils.py           # Utility functions (logging, etc.).
├── requirements.txt       # Project dependencies.
├── README.md              # Project documentation.
```

---

## Usage

### Command Execution

Run the main script by providing the URL of the page you want to scrape. You can also specify the optional maximum depth.

```bash
$ python main.py <url> [max_depth=1]
```

### Example

```bash
$ python main.py https://example.com 2
```

In this example, the scraper will analyze `https://example.com` up to a depth of 2 levels.

---

## Features

### Content Extraction

The scraper extracts:

- **Title and meta tags**.
- **Headings** (h1, h2, etc.).
- **Text** (paragraphs).
- **Images** (src, alt).
- **Emails**.
- **Products**.
- **Forms** (method, action, fields).

### Analysis

1. **Repeated IDs**: Identifies elements with the same `id`.
2. **H1 Headers**: Checks if missing or multiple headers exist.
3. **Meta Description**: Detects if the meta description is missing.
4. **Mismatched Links**: Finds social media links that do not match their text or icons.
5. **CMS Detection**: Identifies the platform (WordPress, Shopify, etc.) and frameworks (Laravel, Django, etc.).

### Saving Results

Extracted data is stored in a JSON file inside the `analysis_scraping` folder.

---

## Main Files

### `main.py`

The project's entry point. Provides the main functionality to execute scraping from the command line.

### `scraper/core.py`

Main class **`WebScraper`**:

- Performs depth-first scraping (BFS).
- Uses **requests-html** to render basic JavaScript.
- Extracts main content from pages.
- Implements logic to analyze visited URLs.

### `scraper/analysis.py`

Performs web page analysis, including:

- Repeated IDs.
- Header analysis.
- Meta tag review.
- CMS and framework detection.

### `scraper/utils.py`

Helper functions such as logging configuration.

---

## Customization

### Adjusting the `WebScraper` Class

- **`timeout`**: Maximum wait time for HTTP requests.
- **`sleep_time`**: Wait time after rendering a page.
- **`scrolldown`**: Number of scrolls to simulate during rendering.

### Extensions

You can extend the functionality by adding:

1. New checks in `scraper/analysis.py`.
2. New extraction methods in `scraper/core.py`.

---

## Notes

- This project is designed for ethical scraping. Check the website's terms of service before using it.
- If you encounter issues, review the generated logs for detailed information.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

## Contact

For questions or comments, you can reach the developer at:

- **Email**: [info@albertomier.com](mailto:info@albertomier.com)
- **Website**: [albertomier.com](https://albertomier.com)

