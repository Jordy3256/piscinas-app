from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.units import mm


AZUL = colors.HexColor("#123B66")
CELESTE = colors.HexColor("#0B8FD3")
GRIS = colors.HexColor("#64748B")
LINEA = colors.HexColor("#D9E3EC")


def _logo_path():
    return Path(settings.BASE_DIR) / "finanzas" / "static" / "finanzas" / "img" / "jvaqua_logo.png"


def draw_jvaqua_pdf_page(canvas, doc):
    """
    Cabecera y pie corporativos reutilizables para reportes PDF.

    El logotipo se dibuja en la zona reservada por topMargin. Las vistas que
    usen este callback deben dejar al menos ~22 mm de margen superior.
    """
    canvas.saveState()
    page_width, page_height = canvas._pagesize

    # Cabecera.
    if not getattr(doc, "jvaqua_skip_header", False):
        logo = _logo_path()
        x = getattr(doc, "leftMargin", 14 * mm)
        y = page_height - 15 * mm
        if logo.exists():
            canvas.drawImage(
                str(logo),
                x,
                y,
                width=18 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                anchor="w",
                mask="auto",
            )
        else:
            canvas.setFillColor(AZUL)
            canvas.setFont("Helvetica-Bold", 12)
            canvas.drawString(x, page_height - 10 * mm, "JVAQUA")

        canvas.setFillColor(GRIS)
        canvas.setFont("Helvetica-Bold", 7.2)
        canvas.drawRightString(
            page_width - getattr(doc, "rightMargin", 14 * mm),
            page_height - 9.5 * mm,
            "JVAQUA POOL SERVICES",
        )
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.45)
        canvas.line(
            getattr(doc, "leftMargin", 14 * mm),
            page_height - 20 * mm,
            page_width - getattr(doc, "rightMargin", 14 * mm),
            page_height - 20 * mm,
        )

    # Pie.
    canvas.setStrokeColor(LINEA)
    canvas.setLineWidth(0.35)
    canvas.line(
        getattr(doc, "leftMargin", 14 * mm),
        11 * mm,
        page_width - getattr(doc, "rightMargin", 14 * mm),
        11 * mm,
    )
    canvas.setFillColor(GRIS)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        getattr(doc, "leftMargin", 14 * mm),
        7 * mm,
        "JVAQUA · aquo360.com",
    )
    canvas.drawRightString(
        page_width - getattr(doc, "rightMargin", 14 * mm),
        7 * mm,
        f"Página {doc.page}",
    )
    canvas.restoreState()
