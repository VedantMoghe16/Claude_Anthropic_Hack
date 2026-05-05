"""
Adhikar-Aina | certificate.py

Replaces: 05_adhikar_certificates.py
# DATABRICKS REMOVED: Spark DataFrames + Delta table + to_json() replaced with ReportLab PDF

Generates the Adhikar Certificate PDF with:
  1. Header — "ADHIKAR — Aapka Adhikar, Aapki Pehchaan" + citizen name + masked Aadhaar
  2. Entitlement table — scheme name, benefit, ministry
  3. Legal basis — Act / Section per scheme
  4. Claim script — Hindi + English ("Main [name] hun...")
  5. Grievance contacts — officer name, phone, email, district office
  6. Footer — "Agar koi inkaar kare — yeh certificate legal proof hai"
"""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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

# ── Unicode font detection (for Hindi / Devanagari rendering) ─────────────────

_HINDI_FONT = "Helvetica"

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
            _HINDI_FONT = "UniFont"
        except Exception:
            pass
        break

# ── Legal acts mapping keyed on scheme category keywords ─────────────────────

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
        str(scheme.get("scheme_category","")).lower(),
        str(scheme.get("tags","")).lower(),
        str(scheme.get("scheme_name","")).lower(),
        str(scheme.get("eligibility_text","")).lower(),
    ])
    for keyword, basis in _LEGAL_BASIS.items():
        if keyword in combined:
            return basis
    return "Government Welfare Scheme Act — as notified by the concerned Ministry/Department"


def _mask_aadhaar(aadhar: str) -> str:
    a = str(aadhar).strip()
    if len(a) >= 4:
        return "XXXX-XXXX-" + a[-4:]
    return "XXXX-XXXX-XXXX"


def _claim_script(name: str, aadhar: str, scheme_name: str, legal_basis: str) -> str:
    masked = _mask_aadhaar(aadhar)
    first_act = legal_basis.split(";")[0].split("(")[0].strip()
    romanized = (
        f"Main {name} hun, mera Aadhaar {masked} hai.\n"
        f"Mujhe '{scheme_name}' ka haq hai\n"
        f"{first_act} ke tahat."
    )
    english = (
        f"I am {name}. My Aadhaar is {masked}.\n"
        f"I am legally entitled to '{scheme_name}' under {first_act}.\n"
        f"Please process my claim immediately."
    )
    return romanized + "\n\n" + english


def _grievance_contacts(district: str) -> List[Dict[str, str]]:
    d = district or "Your District"
    return [
        {
            "officer": "District Collector / DM",
            "phone":   "1800-11-0001 (National Helpline, Free)",
            "email":   f"collector.{d[:6].lower()}@gov.in",
            "address": f"District Collectorate, {d}, Maharashtra",
        },
        {
            "officer": "District Legal Services Authority (DLSA)",
            "phone":   "1800-233-4415 (Toll-free)",
            "email":   "dlsa@maharashtra.gov.in",
            "address": f"District Court Complex, {d}",
        },
        {
            "officer": "Maharashtra Grievance Portal",
            "phone":   "1800-120-8040",
            "email":   "pgrs@maharashtra.gov.in",
            "address": "grievances.maharashtra.gov.in",
        },
    ]


# ── PDF generation ────────────────────────────────────────────────────────────

def generate_pdf(
    citizen:     Dict[str, Any],
    schemes:     List[Dict[str, Any]],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate Adhikar Certificate PDF.
    Returns the Path of the saved file.
    """
    # DATABRICKS REMOVED: Delta table write + to_json() → ReportLab PDF
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts  = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        cid = citizen.get("citizen_id", citizen.get("aadhar","UNK"))
        output_path = CERTS_DIR / f"adhikar_{cid}_{ts}.pdf"

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
    )

    GREEN = colors.HexColor("#16a34a")
    AMBER = colors.HexColor("#d97706")
    LIGHT = colors.HexColor("#f0fdf4")
    DARK  = colors.HexColor("#1f2937")
    RED   = colors.HexColor("#dc2626")

    H1   = ParagraphStyle("H1",   fontSize=18, textColor=GREEN, spaceAfter=4,
                           fontName="Helvetica-Bold", alignment=1)
    H2   = ParagraphStyle("H2",   fontSize=13, textColor=GREEN, spaceAfter=4,
                           fontName="Helvetica-Bold")
    H3   = ParagraphStyle("H3",   fontSize=10, textColor=DARK,  spaceAfter=3,
                           fontName="Helvetica-Bold")
    BODY = ParagraphStyle("BODY", fontSize=8,  textColor=DARK,  spaceAfter=3,
                           fontName="Helvetica", leading=12)
    MONO = ParagraphStyle("MONO", fontSize=8,  fontName="Courier",
                           textColor=colors.HexColor("#1e40af"), leading=12)
    WARN = ParagraphStyle("WARN", fontSize=9,  textColor=RED, fontName="Helvetica-Bold")
    FOOT = ParagraphStyle("FOOT", fontSize=7,  textColor=colors.gray, alignment=1)

    story = []

    # ── 1. HEADER ─────────────────────────────────────────────────────────────
    story.append(Paragraph("ADHIKAR — Aapka Adhikar, Aapki Pehchaan", H1))
    story.append(Paragraph(
        "Certificate of Entitlement &amp; Legal Rights — Government Welfare Schemes",
        ParagraphStyle("sub", fontSize=10, textColor=colors.gray, alignment=1, fontName="Helvetica")
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN))
    story.append(Spacer(1, 0.3*cm))

    name     = citizen.get("name", "Citizen")
    aadhar   = str(citizen.get("aadhar","000000000000"))
    district = citizen.get("district","N/A")
    cert_id  = f"AC-{district[:3].upper()}-{aadhar[-4:]}-{datetime.utcnow().strftime('%Y%m%d')}"
    issued   = datetime.utcnow().strftime("%d %B %Y")

    info = [
        ["Citizen Name:",  name,                  "Certificate ID:", cert_id],
        ["Aadhaar No.:",   _mask_aadhaar(aadhar), "Issued On:",      issued],
        ["District:",      district,              "Income Bracket:", citizen.get("income_bracket","N/A")],
        ["Caste Category:",citizen.get("caste_category","N/A"),
         "Occupation:",    citizen.get("occupation","N/A")],
    ]
    t_info = Table(info, colWidths=[3.5*cm, 6.5*cm, 3.5*cm, 6*cm])
    t_info.setStyle(TableStyle([
        ("FONTNAME",        (0,0),(-1,-1), "Helvetica"),
        ("FONTNAME",        (0,0),(0,-1),  "Helvetica-Bold"),
        ("FONTNAME",        (2,0),(2,-1),  "Helvetica-Bold"),
        ("FONTSIZE",        (0,0),(-1,-1), 8),
        ("TEXTCOLOR",       (0,0),(0,-1),  GREEN),
        ("TEXTCOLOR",       (2,0),(2,-1),  GREEN),
        ("BACKGROUND",      (0,0),(-1,-1), LIGHT),
        ("GRID",            (0,0),(-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS",  (0,0),(-1,-1), [LIGHT, colors.white]),
        ("TOPPADDING",      (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",   (0,0),(-1,-1), 4),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 0.4*cm))

    # ── 2. ENTITLED SCHEMES TABLE ─────────────────────────────────────────────
    story.append(Paragraph(f"Schemes You Are Entitled To ({len(schemes)} found)", H2))
    header = [["#", "Scheme Name", "Benefit", "Ministry"]]
    rows   = [[
        str(i),
        Paragraph(textwrap.fill(s["scheme_name"], 38), BODY),
        Paragraph(textwrap.fill(str(s["benefit"])[:130], 28), BODY),
        Paragraph(textwrap.fill(str(s.get("ministry","Government"))[:45], 22), BODY),
    ] for i, s in enumerate(schemes, 1)]
    t_schemes = Table(header + rows, colWidths=[0.6*cm, 7.2*cm, 5.8*cm, 4.4*cm])
    t_schemes.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(-1,0),  GREEN),
        ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
        ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0,0),(-1,0),  8),
        ("GRID",           (0,0),(-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, LIGHT]),
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",     (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
    ]))
    story.append(t_schemes)
    story.append(Spacer(1, 0.4*cm))

    # ── 3 + 4. PER-SCHEME LEGAL BASIS & CLAIM SCRIPT ─────────────────────────
    story.append(Paragraph("Your Legal Rights &amp; Claim Script Per Scheme", H2))
    for s in schemes:
        legal  = _get_legal_basis(s)
        script = _claim_script(name, aadhar, s["scheme_name"], legal)
        story.append(Paragraph(s["scheme_name"], H3))
        story.append(Paragraph(f"<b>Legal Basis:</b> {legal}", BODY))
        story.append(Paragraph("<b>Claim Script (say / show this to any official):</b>", BODY))
        story.append(Paragraph(script.replace("\n", "<br/>"), MONO))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.lightgrey))
        story.append(Spacer(1, 0.15*cm))

    # ── 5. GRIEVANCE CONTACTS ─────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Grievance Contacts — Agar Koi Inkaar Kare", H2))
    contacts = _grievance_contacts(district)
    c_header = [["Officer / Authority", "Helpline", "Email / Address"]]
    c_rows   = [[c["officer"], c["phone"], f"{c['email']}\n{c['address']}"]
                for c in contacts]
    t_contacts = Table(c_header + c_rows, colWidths=[5*cm, 4.5*cm, 9*cm])
    t_contacts.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  AMBER),
        ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#fef3c7")]),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
    ]))
    story.append(t_contacts)
    story.append(Spacer(1, 0.4*cm))

    # ── 6. FOOTER ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Agar koi inkaar kare — yeh certificate legal proof hai | "
        "If anyone denies your rights, this certificate is legal proof.",
        WARN
    ))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"Generated by ADHIKAR — Sovereign Citizen Rights Platform | "
        f"Certificate ID: {cert_id} | Date: {issued}",
        FOOT
    ))
    story.append(Paragraph(
        "RTI Act 2005 | NSAP | Consumer Protection Act 2019 | Legal Services Authorities Act 1987",
        FOOT
    ))

    doc.build(story)
    return output_path
