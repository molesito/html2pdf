import io
import re
import asyncio
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

PAGE_BREAK_TOKEN = r"\[NUEVA PÁGINA\]"

def normalize_html(raw_html: str) -> str:
    # Limpia saltos de línea alrededor del marcador y lo sustituye por salto real
    cleaned = re.sub(r"\n*\s*\[NUEVA PÁGINA\]\s*\n*", "[NUEVA PÁGINA]", raw_html, flags=re.IGNORECASE)
    return re.sub(PAGE_BREAK_TOKEN, '<div class="page-break"></div>', cleaned, flags=re.IGNORECASE)

async def html_to_pdf_bytes(html: str) -> bytes:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ])
        page = await browser.new_page()

        # CSS base A4 + tablas + saltos
        base_css = """
        <style>
          @page { size: A4; margin: 18mm; }
          .page-break { break-before: page; }
          table, th, td { border: 1px solid black; border-collapse: collapse; }
          th, td { padding: 4px; }
        </style>
        """

        # Si no viene documento completo, lo envolvemos + MathJax
        if "<html" not in html.lower():
            html = f"<!DOCTYPE html><html lang='es'><head><meta charset='UTF-8'>{base_css}" \
                   f"<script src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'></script>" \
                   f"</head><body>{html}</body></html>"
        else:
            # Inyecta CSS base si no está
            html = re.sub(r"(?i)</head>", base_css + "</head>", html, count=1)

        # Carga sin esperar recursos infinitos
        await page.set_content(html, wait_until="domcontentloaded")

        # Intenta esperar a MathJax
        try:
            await page.wait_for_function("window.MathJax && MathJax.typesetPromise", timeout=4000)
            await page.evaluate("return MathJax.typesetPromise()")
        except Exception:
            pass

        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "18mm", "bottom": "18mm", "left": "18mm", "right": "18mm"}
        )
        await browser.close()
        return pdf_bytes

@app.post("/html2pdf")
def html2pdf():
    data = request.get_json(silent=True)
    if not data or "html" not in data:
        return jsonify({"error": "Bad request: falta 'html'"}), 400

    html = normalize_html(data["html"])
    pdf_bytes = asyncio.run(html_to_pdf_bytes(html))
    filename = (data.get("filename") or "documento") + ".pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

@app.get("/")
def root():
    return jsonify({"ok": True, "service": "html2pdf", "endpoint": "/html2pdf"})

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=True)
