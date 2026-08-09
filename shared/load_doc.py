import requests, re
import pypdf, fitz          # fitz = pymupdf

def load_pdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        text = page.get_text("text")  # better extraction than pypdf
        if not text or len(text.strip()) < 50:
            continue
        # Fix hyphenation only
        text = re.sub(r'-\n', '', text)
        text = re.sub(r'\n(?=[a-z])', ' ', text)
        lines = [l for l in text.split("\n")
                 if len(l.strip()) > 20
                 and not l.strip().replace(".", "").replace(" ", "").isdigit()
                 and "....." not in l]
        pages.append("\n".join(lines))
    return "\n\n".join(pages)

def load_text(filepath: str) -> str:
    return open(filepath, "r").read()

def load_url(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    return response.text[:50000]  # cap to avoid massive pages