"""
Adhikar-Aina | certificate.py

Generates a formal Adhikar Certificate PDF:
  - Government document style: navy + gold colors, double page border
  - Citizen info grid, scheme entitlement table, legal basis, claim scripts
  - Multilingual support via Sarvam AI (22 Indian languages)

Usage:
    from certificate import generate_pdf
    path = generate_pdf(citizen, schemes, output_path=Path("cert.pdf"), language="hi")
"""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

sys.path.insert(0, str(Path(__file__).parent))
from config import CERTS_DIR

# ── Unicode font detection ─────────────────────────────────────────────────────

_BODY_FONT = "Helvetica"
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf",
    "/Library/Fonts/Arial Unicode MS.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
for _fp in _FONT_CANDIDATES:
    if Path(_fp).exists():
        try:
            pdfmetrics.registerFont(TTFont("UniFont", _fp))
            _BODY_FONT = "UniFont"
        except Exception:
            pass
        break

# ── Colors ─────────────────────────────────────────────────────────────────────

NAVY  = colors.HexColor("#1a3a6b")
GOLD  = colors.HexColor("#c8a44e")
CREAM = colors.HexColor("#faf8f2")
LIGHT = colors.HexColor("#eef2f8")
DARK  = colors.HexColor("#1f2937")
RED   = colors.HexColor("#dc2626")
WHITE = colors.white

# ── Translation helper ─────────────────────────────────────────────────────────

def _T(text: str, lang: str) -> str:
    """Translate `text` to `lang` via Sarvam AI; returns original on any error."""
    if lang in ("en", "") or not text.strip():
        return text
    try:
        from sarvam import translate
        return translate(text, target_lang=lang, source_lang="en")
    except Exception:
        return text


# ── Legal acts lookup ─────────────────────────────────────────────────────────

_LEGAL_BASIS: Dict[str, str] = {
    "agriculture": "PM-KISAN Scheme Guidelines; Agricultural Produce Marketing Act",
    "rural":       "MGNREGA 2005 (Section 3); National Rural Livelihood Mission",
    "education":   "Right to Education Act 2009 (Section 3 & 12); PM Scholarship Scheme",
    "women":       "Women & Child Development Act; PCMA 2006; PM Matru Vandana Yojana",
    "child":       "Integrated Child Development Services Act; NHM Guidelines",
    "health":      "PM Ayushman Bharat (PMJAY) Guidelines; National Health Mission Act",
    "housing":     "Pradhan Mantri Awas Yojana (PMAY) Guidelines; Section 21",
    "skill":       "Skill India Mission; PM Kaushal Vikas Yojana (PMKVY) Guidelines",
    "business":    "MSME Development Act 2006; Stand Up India Scheme",
    "msme":        "MSME Development Act 2006; PMEGP Guidelines",
    "tribal":      "PESA Act 1996; Forest Rights Act 2006",
    "sc":          "Scheduled Castes Sub-Plan; Dr. Ambedkar Foundation Scheme",
    "st":          "PESA Act 1996; Forest Rights Act 2006; ST Development Scheme",
    "obc":         "OBC Welfare Scheme Guidelines; Mandal Commission Recommendations",
    "social":      "National Social Assistance Programme (NSAP); NFSA 2013",
    "employment":  "MGNREGA 2005; PM Rojgar Protsahan Yojana",
    "fishermen":   "Marine Fisheries Regulation Act; PMMSY Scheme",
    "labour":      "Labour Welfare Fund Act; Building & Construction Workers Act 1996",
}


def _get_legal_basis(scheme: Dict[str, Any]) -> str:
    combined = " ".join([
        str(scheme.get("scheme_category", "")).lower(),
        str(scheme.get("tags", "")).lower(),
        str(scheme.get("scheme_name", "")).lower(),
        str(scheme.get("eligibility_text", "")).lower(),
    ])
    for keyword, basis in _LEGAL_BASIS.items():
        if keyword in combined:
            return basis
    return "Government Welfare Scheme Act — as notified by the concerned Ministry/Department"


def _mask_aadhaar(aadhar: str) -> str:
    a = str(aadhar).strip()
    return ("XXXX-XXXX-" + a[-4:]) if len(a) >= 4 else "XXXX-XXXX-XXXX"


def _claim_script(name: str, aadhar: str, scheme_name: str, legal_basis: str) -> str:
    masked    = _mask_aadhaar(aadhar)
    first_act = legal_basis.split(";")[0].split("(")[0].strip()
    return (
        f"I am {name}. My Aadhaar is {masked}.\n"
        f"I am legally entitled to '{scheme_name}' under {first_act}.\n"
        f"Please process my claim immediately.\n\n"
        f"Main {name} hun, mera Aadhaar {masked} hai.\n"
        f"Mujhe '{scheme_name}' ka haq hai {first_act} ke tahat.\n"
        f"Kripya mera dawa turant process karein."
    )


def _grievance_contacts(district: str) -> List[Dict[str, str]]:
    d = district or "Your District"
    return [
        {
            "officer": "District Collector / DM",
            "phone":   "1800-11-0001 (National, Free)",
            "contact": f"collector.{d[:6].lower()}@gov.in | District Collectorate, {d}",
        },
        {
            "officer": "District Legal Services Authority",
            "phone":   "1800-233-4415 (Toll-free)",
            "contact": "dlsa@gov.in | District Court Complex",
        },
        {
            "officer": "National Grievance Portal",
            "phone":   "1800-120-8040",
            "contact": "pgportal.gov.in",
        },
    ]


# ── Page border (drawn on every page via canvas callback) ─────────────────────

def _draw_page_border(canvas, doc):
    w, h = A4
    canvas.saveState()
    # Outer border — navy
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(3)
    canvas.rect(0.75*cm, 0.75*cm, w - 1.5*cm, h - 1.5*cm)
    # Inner border — gold
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.2)
    canvas.rect(1.0*cm, 1.0*cm, w - 2.0*cm, h - 2.0*cm)
    # Gold corner squares
    sq = 0.22*cm
    for cx, cy in [
        (0.75*cm, 0.75*cm),
        (w - 0.75*cm - sq, 0.75*cm),
        (0.75*cm, h - 0.75*cm - sq),
        (w - 0.75*cm - sq, h - 0.75*cm - sq),
    ]:
        canvas.setFillColor(GOLD)
        canvas.rect(cx, cy, sq, sq, fill=1, stroke=0)
    canvas.restoreState()


# ── PDF generation ─────────────────────────────────────────────────────────────

def generate_pdf(
    citizen:     Dict[str, Any],
    schemes:     List[Dict[str, Any]],
    output_path: Optional[Path] = None,
    language:    str = "en",
) -> Path:
    """
    Generate Adhikar Certificate PDF.
    `language` is a short code ('hi', 'mr', 'ta', …) or 'en' for English.
    Returns the Path of the saved PDF.
    """
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts  = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        cid = citizen.get("citizen_id", citizen.get("aadhar", "UNK"))
        output_path = CERTS_DIR / f"adhikar_{cid}_{ts}.pdf"

    lang = language or "en"

    def T(text: str) -> str:
        return _T(text, lang)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        rightMargin=2.3*cm, leftMargin=2.3*cm,
        topMargin=2.3*cm,   bottomMargin=2.3*cm,
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    f      = _BODY_FONT
    f_bold = "Helvetica-Bold" if f == "Helvetica" else f

    TITLE   = ParagraphStyle("TITLE",  fontSize=22, textColor=NAVY, alignment=TA_CENTER,
                              fontName=f_bold, spaceAfter=2, leading=26)
    SUB     = ParagraphStyle("SUB",    fontSize=9,  textColor=GOLD, alignment=TA_CENTER,
                              fontName=f, spaceAfter=2, leading=12)
    GOV_HDR = ParagraphStyle("GOV",    fontSize=8,  textColor=colors.gray, alignment=TA_CENTER,
                              fontName=f, spaceAfter=1, leading=10)
    H2      = ParagraphStyle("H2",     fontSize=10, textColor=NAVY,
                              fontName=f_bold, spaceAfter=3, spaceBefore=6)
    H3      = ParagraphStyle("H3",     fontSize=9,  textColor=NAVY,
                              fontName=f_bold, spaceAfter=2, spaceBefore=3)
    BODY    = ParagraphStyle("BODY",   fontSize=8,  textColor=DARK,
                              fontName=f, spaceAfter=2, leading=11)
    MONO    = ParagraphStyle("MONO",   fontSize=8,  fontName="Courier",
                              textColor=NAVY, leading=12)
    WARN    = ParagraphStyle("WARN",   fontSize=9,  textColor=RED,
                              fontName=f_bold, alignment=TA_CENTER)
    FOOT    = ParagraphStyle("FOOT",   fontSize=7,  textColor=colors.gray,
                              alignment=TA_CENTER, fontName=f)
    CERTID  = ParagraphStyle("CERTID", fontSize=9,  textColor=WHITE,
                              alignment=TA_CENTER, fontName=f_bold)
    LBL     = ParagraphStyle("LBL",    fontSize=8,  textColor=NAVY,
                              fontName=f_bold, leading=11)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("⚖  Government of India  ·  भारत सरकार  ⚖", GOV_HDR))
    story.append(Paragraph("Ministry of Social Justice, Empowerment &amp; Tribal Welfare", GOV_HDR))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph("ADHIKAR", TITLE))
    story.append(Paragraph("Aapka Adhikar, Aapki Pehchaan  —  Your Rights, Your Identity", SUB))
    story.append(Paragraph(
        T("Certificate of Entitlement &amp; Legal Rights — Government Welfare Schemes"),
        ParagraphStyle("csub", fontSize=9, textColor=DARK, alignment=TA_CENTER, fontName=f)
    ))
    story.append(Spacer(1, 0.25*cm))
    story.append(HRFlowable(width="100%", thickness=2.0, color=NAVY))
    story.append(HRFlowable(width="100%", thickness=0.6, color=GOLD, spaceAfter=3))
    story.append(Spacer(1, 0.15*cm))

    # ── Certificate ID banner ─────────────────────────────────────────────────
    name     = citizen.get("name", "Citizen")
    aadhar   = str(citizen.get("aadhar", "000000000000"))
    district = citizen.get("district", "N/A")
    state    = citizen.get("state", "N/A")
    cert_id  = f"AC-{district[:3].upper()}-{aadhar[-4:]}-{datetime.utcnow().strftime('%Y%m%d')}"
    issued   = datetime.utcnow().strftime("%d %B %Y")

    banner = [[Paragraph(
        f"  {T('Certificate ID')}: {cert_id}  |  {T('Issued On')}: {issued}  |  {T('Valid For')}: 180 {T('Days')}  ",
        CERTID
    )]]
    t_banner = Table(banner, colWidths=[doc.width])
    t_banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 0.3*cm))

    # ── Citizen info grid ─────────────────────────────────────────────────────
    story.append(Paragraph(T("Citizen Profile"), H2))

    income_val = citizen.get("annual_income", citizen.get("income_bracket", "N/A"))
    try:
        income_val = f"Rs {int(float(str(income_val).replace(',', ''))):,}"
    except Exception:
        income_val = str(income_val)

    def lbl(text):
        return Paragraph(text, LBL)

    def val(text):
        return Paragraph(str(text), BODY)

    info_rows = [
        [lbl(T("Full Name")),       val(name),
         lbl(T("Certificate ID")),  val(cert_id)],
        [lbl(T("Aadhaar No.")),     val(_mask_aadhaar(aadhar)),
         lbl(T("Issued On")),       val(issued)],
        [lbl(T("District / State")), val(f"{district}, {state}"),
         lbl(T("Annual Income")),   val(income_val)],
        [lbl(T("Caste Category")),  val(citizen.get("caste_category", "N/A")),
         lbl(T("Occupation")),      val(str(citizen.get("occupation", "N/A")).title())],
    ]
    t_info = Table(info_rows, colWidths=[3.8*cm, 5.8*cm, 3.8*cm, 5.8*cm])
    t_info.setStyle(TableStyle([
        ("FONTSIZE",       (0,0),(-1,-1), 8),
        ("BACKGROUND",     (0,0),(-1,-1), CREAM),
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [CREAM, WHITE]),
        ("GRID",           (0,0),(-1,-1), 0.3, GOLD),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ("LEFTPADDING",    (0,0),(-1,-1), 5),
        ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 0.4*cm))

    # ── Scheme entitlement table ──────────────────────────────────────────────
    story.append(Paragraph(T(f"Schemes You Are Entitled To  ({len(schemes)} identified)"), H2))

    header = [[
        Paragraph(T("#"),                       CERTID),
        Paragraph(T("Scheme Name"),             CERTID),
        Paragraph(T("Benefit / Amount"),        CERTID),
        Paragraph(T("Ministry / Department"),   CERTID),
    ]]
    rows = [[
        Paragraph(str(i), BODY),
        Paragraph(textwrap.fill(T(s["scheme_name"]), 38), BODY),
        Paragraph(textwrap.fill(T(str(s.get("benefit", "As per scheme guidelines")))[:130], 28), BODY),
        Paragraph(textwrap.fill(T(str(s.get("ministry", "Government of India")))[:45], 22), BODY),
    ] for i, s in enumerate(schemes, 1)]

    t_schemes = Table(header + rows, colWidths=[0.7*cm, 7.0*cm, 5.6*cm, 5.0*cm])
    t_schemes.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  NAVY),
        ("TEXTCOLOR",      (0,0),(-1,0),  WHITE),
        ("FONTNAME",       (0,0),(-1,0),  f_bold),
        ("FONTSIZE",       (0,0),(-1,-1), 8),
        ("GRID",           (0,0),(-1,-1), 0.3, colors.HexColor("#c8c8c8")),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, LIGHT]),
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ("LEFTPADDING",    (0,0),(-1,-1), 4),
    ]))
    story.append(t_schemes)
    story.append(Spacer(1, 0.4*cm))

    # ── Per-scheme legal basis & claim script ─────────────────────────────────
    story.append(Paragraph(T("Legal Rights &amp; Claim Script Per Scheme"), H2))
    for s in schemes:
        legal  = _get_legal_basis(s)
        script = _claim_script(name, aadhar, s["scheme_name"], legal)

        story.append(Paragraph(T(s["scheme_name"]), H3))
        story.append(Paragraph(
            f"<b>{T('Legal Basis')}:</b>  {T(legal)}", BODY
        ))
        story.append(Paragraph(
            f"<b>{T('Claim Script')} — {T('Say or show this to any official')}:</b>", BODY
        ))
        translated_script = T(script) if lang != "en" else script
        script_table = [[Paragraph(translated_script.replace("\n", "<br/>"), MONO)]]
        t_script = Table(script_table, colWidths=[doc.width])
        t_script.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), LIGHT),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("BOX",           (0,0),(-1,-1), 0.5, GOLD),
        ]))
        story.append(t_script)
        story.append(HRFlowable(width="100%", thickness=0.4, color=GOLD, spaceAfter=4))
        story.append(Spacer(1, 0.05*cm))

    # ── Grievance contacts ────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(T("Grievance Contacts — If Anyone Denies Your Rights"), H2))
    contacts = _grievance_contacts(district)
    c_header = [[
        Paragraph(T("Officer / Authority"),  CERTID),
        Paragraph(T("Helpline"),             CERTID),
        Paragraph(T("Contact / Address"),    CERTID),
    ]]
    c_rows = [[
        Paragraph(T(c["officer"]), BODY),
        Paragraph(c["phone"],      BODY),
        Paragraph(c["contact"],    BODY),
    ] for c in contacts]

    t_contacts = Table(c_header + c_rows, colWidths=[5.2*cm, 4.8*cm, 8.2*cm])
    t_contacts.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  GOLD),
        ("FONTNAME",      (0,0),(-1,0),  f_bold),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#c8c8c8")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, colors.HexColor("#fef9ec")]),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
    ]))
    story.append(t_contacts)
    story.append(Spacer(1, 0.4*cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD))
    story.append(HRFlowable(width="100%", thickness=2.0, color=NAVY))
    story.append(Spacer(1, 0.15*cm))

    warn_text = T("If anyone denies your rights — this certificate is legal proof.")
    warn_data = [[Paragraph(f"⚠  {warn_text}  ⚠", WARN)]]
    t_warn = Table(warn_data, colWidths=[doc.width])
    t_warn.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#fff0f0")),
        ("BOX",           (0,0),(-1,-1), 1.0, RED),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]))
    story.append(t_warn)
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"Generated by ADHIKAR — Claude Hackathon 2025  |  "
        f"Certificate ID: {cert_id}  |  {T('Date')}: {issued}",
        FOOT
    ))
    story.append(Paragraph(
        "RTI Act 2005  |  NSAP  |  Consumer Protection Act 2019  |  Legal Services Authorities Act 1987",
        FOOT
    ))

    doc.build(story, onFirstPage=_draw_page_border, onLaterPages=_draw_page_border)
    return output_path
