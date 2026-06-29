"""build_pdf.py — Génère rapport.pdf à partir de rapport.md.

Conversion reproductible Markdown -> HTML -> PDF, sans dépendance système
(pip : markdown + xhtml2pdf). Lancer : `python rapport/build_pdf.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa

DOSSIER = Path(__file__).resolve().parent
SOURCE = DOSSIER / "rapport.md"
SORTIE = DOSSIER / "rapport.pdf"

# Mise en forme simple et lisible pour l'impression.
CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.4; color: #222; }
h1 { font-size: 20pt; color: #1a3c6e; border-bottom: 2px solid #1a3c6e;
     padding-bottom: 4px; }
h2 { font-size: 14pt; color: #1a3c6e; margin-top: 18px; }
h3 { font-size: 11.5pt; color: #333; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #aaa; padding: 4px 6px; font-size: 9.5pt; }
th { background: #e8eef7; }
blockquote { background: #f4f6fa; border-left: 4px solid #1a3c6e;
             padding: 6px 10px; color: #333; }
code { background: #f0f0f0; padding: 1px 3px; font-size: 9.5pt; }
hr { border: none; border-top: 1px solid #ccc; }
"""


def main() -> None:
    texte = SOURCE.read_text(encoding="utf-8")
    corps = markdown.markdown(
        texte, extensions=["tables", "fenced_code", "sane_lists"])
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head>" \
           f"<body>{corps}</body></html>"

    with open(SORTIE, "wb") as f:
        resultat = pisa.CreatePDF(html, dest=f, encoding="utf-8")
    if resultat.err:
        print("Erreur lors de la génération du PDF.", file=sys.stderr)
        sys.exit(1)
    print(f"Écrit : {SORTIE.relative_to(DOSSIER.parent)}")


if __name__ == "__main__":
    main()
