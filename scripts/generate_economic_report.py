"""Generate PDF report on US economic intervention in Chile during Allende's government."""

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Base URL for the external document viewer
DOCUMENT_VIEWER_BASE_URL = "https://declasseuucl.vercel.app"


def get_document_url(doc_id: str) -> str:
    """Generate URL for viewing a document in the web viewer.

    This matches the URL format used in the GitHub Pages report.

    Args:
        doc_id: Document ID (e.g., "25031")

    Returns:
        URL to view document in the web viewer
    """
    return f"{DOCUMENT_VIEWER_BASE_URL}/?currentPage=1&documentId={doc_id}"


def get_pdf_download_url(doc_id: str) -> str:
    """Generate direct PDF download URL for a document.

    Args:
        doc_id: Document ID (e.g., "25031")

    Returns:
        Direct URL to download the PDF file
    """
    return f"{DOCUMENT_VIEWER_BASE_URL}/api/{doc_id}/download/pdf"


def doc_link(doc_id: str, text: str | None = None) -> str:
    """Generate HTML link to a document.

    Args:
        doc_id: Document ID
        text: Link text (defaults to "Document {doc_id}")

    Returns:
        HTML anchor tag with link
    """
    url = get_document_url(doc_id)
    display_text = text or f"Document {doc_id}"
    return f'<a href="{url}" color="blue">{display_text}</a>'


def create_report(output_path: Path) -> None:
    """Create the PDF report."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # Center
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.grey,
        alignment=1,
        spaceAfter=30,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#1a365d"),
    )

    subheading_style = ParagraphStyle(
        "SubHeading",
        parent=styles["Heading3"],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor("#2c5282"),
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        spaceBefore=6,
        spaceAfter=6,
        leading=14,
    )

    quote_style = ParagraphStyle(
        "Quote",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=10,
        spaceAfter=10,
        leading=14,
        textColor=colors.HexColor("#4a5568"),
        backColor=colors.HexColor("#f7fafc"),
        borderPadding=10,
    )

    source_style = ParagraphStyle(
        "Source",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#718096"),
        spaceBefore=4,
    )

    link_style = ParagraphStyle(
        "Link",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#2b6cb0"),
        spaceBefore=2,
    )

    # Build content
    story = []

    # Title
    story.append(
        Paragraph(
            "US Economic Intervention in Chile<br/>During Allende's Government (1970-1973)",
            title_style,
        )
    )
    story.append(
        Paragraph(
            "Evidence from Declassified CIA Documents",
            subtitle_style,
        )
    )
    story.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y')} | Source: RAG Index v1.0.0 (5,666 documents, 12,811 chunks)",
            source_style,
        )
    )
    story.append(Spacer(1, 20))

    # Introduction
    story.append(Paragraph("Research Question", heading_style))
    story.append(
        Paragraph(
            "People justify the military coup under the argument that the economic situation under "
            "Allende's government was very bad. How much of the economic situation during Allende's "
            "government was influenced by the United States?",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "This report presents evidence from declassified CIA documents retrieved through semantic "
            "search of the Desclasificados archive.",
            body_style,
        )
    )

    # Section 1
    story.append(Paragraph("1. Explicit Policy of 'Maximum Economic Pressure'", heading_style))
    story.append(
        Paragraph(
            f'{doc_link("25031")} (TOP SECRET, May 1976) explicitly states US policy:',
            body_style,
        )
    )
    story.append(
        Paragraph(
            '"Basic policy objective of preventing the consolidation of the Allende administration '
            "by using maximum pressure — especially economic pressure — against Chile while "
            'maintaining a restrained public stance."',
            quote_style,
        )
    )
    story.append(
        Paragraph(
            "This confirms that economic destabilization was official US policy, not incidental. "
            "The document reveals that the US pursued this strategy while publicly denying interference.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f'Source: {doc_link("25031", "Doc 25031")}, TOP SECRET Report by Mary P. Chapman',
            source_style,
        )
    )

    # Section 2
    story.append(Paragraph("2. Covert Funding of Opposition and Strikes", heading_style))
    story.append(
        Paragraph(f'{doc_link("24887")} (September 1974) reveals:', body_style)
    )
    story.append(
        Paragraph(
            '"CIA secretly financed striking labor unions and trade groups for over 16 months '
            "before Allende's overthrow, with more than $8 million authorized for clandestine "
            'activities."',
            quote_style,
        )
    )
    story.append(
        Paragraph(
            "This funding supported the truckers' strikes and shop owners' strikes that paralyzed "
            "the Chilean economy in 1972-1973. These strikes created severe shortages and economic "
            "chaos that undermined public confidence in the Allende government.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f'Source: {doc_link("24887", "Doc 24887")}, SECRET Memorandum by Margaret P. Grafeld',
            source_style,
        )
    )

    # Section 3
    story.append(Paragraph("3. Credit Blockade ('Invisible Blockade')", heading_style))
    story.append(
        Paragraph(
            f'{doc_link("25031")} documents systematic US actions through international financial channels:',
            body_style,
        )
    )

    blockade_items = [
        "Paris Club debt renegotiations used as economic pressure",
        "Blocking compensation for nationalized copper companies (Kennecott, Anaconda)",
        "Selective suspension of aid and credits",
        "Coordination with international financial institutions (World Bank, IMF, IDB)",
        "Legal actions to block Chilean copper exports in European courts",
    ]

    for item in blockade_items:
        story.append(Paragraph(f"• {item}", body_style))

    story.append(
        Paragraph(
            "Neither the compensation nor debt issues were resolved before Allende's overthrow "
            "in September 1973, indicating these were used as ongoing pressure tools rather than "
            "genuine negotiations.",
            body_style,
        )
    )

    # Section 4
    story.append(Paragraph("4. Corporate-CIA Coordination", heading_style))

    story.append(Paragraph("ITT Corporation", subheading_style))
    story.append(
        Paragraph(f'{doc_link("24845")} (January 1973) confirms:', body_style)
    )
    story.append(
        Paragraph(
            '"Anti-Allende operation...attention turned to what might be done to prevent '
            'his accession [to power]"',
            quote_style,
        )
    )
    story.append(
        Paragraph(
            f"{doc_link('24842')} references the 'CIA-ITT conversations published in the Anderson papers,' "
            "confirming coordination between the intelligence agency and major US corporations with "
            "interests in Chile.",
            body_style,
        )
    )

    story.append(Paragraph("Copper Companies", subheading_style))
    story.append(
        Paragraph(
            "Kennecott and Anaconda copper companies coordinated with US policy to pressure Chile "
            "over nationalization. The US supported legal actions in European courts to embargo "
            "Chilean copper shipments, directly targeting Chile's primary export revenue.",
            body_style,
        )
    )

    # Section 5
    story.append(Paragraph("5. Track II Operations", heading_style))
    story.append(
        Paragraph(
            f"{doc_link('24885')} explicitly references 'Track II' - the covert operation to prevent "
            "Allende from taking office, which included economic components alongside political "
            "and military tracks. This was a parallel operation hidden even from the US Ambassador "
            "and State Department.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f'Source: {doc_link("24885", "Doc 24885")}, SECRET Memorandum by William G. Hyland',
            source_style,
        )
    )

    # Scale of Intervention Table
    story.append(Paragraph("Scale of US Intervention", heading_style))

    table_data = [
        ["Action", "Amount/Scale", "Period"],
        ["Covert funding (total)", "$8+ million", "1970-1973"],
        ["Support for Frei campaign", "$3 million", "1964"],
        ["Funding to El Mercurio newspaper", "Confirmed (amount redacted)", "1970-1973"],
        ["Financial support to opposition parties", "Ongoing", "1970-1973"],
        ["CIA-funded strikes", "16+ months", "1972-1973"],
    ]

    table = Table(table_data, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ]
        )
    )
    story.append(Spacer(1, 10))
    story.append(table)

    # Key Source Documents Table
    story.append(Paragraph("Key Source Documents", heading_style))
    story.append(
        Paragraph(
            "Click document IDs to view original declassified documents:",
            body_style,
        )
    )

    # Create table with clickable links
    docs_info = [
        ("25031", "May 1976", "TOP SECRET", "Report"),
        ("24916", "Oct 1970", "UNCLASSIFIED", "Memorandum"),
        ("24887", "Sep 1974", "SECRET", "Memorandum"),
        ("24845", "Jan 1973", "UNCLASSIFIED", "Memorandum"),
        ("24885", "Aug 1975", "SECRET", "Memorandum"),
        ("24828", "1969", "UNCLASSIFIED", "Report"),
        ("24918", "Oct 1970", "SECRET", "Report"),
    ]

    docs_data = [
        [
            Paragraph("<b>Document</b>", body_style),
            Paragraph("<b>Date</b>", body_style),
            Paragraph("<b>Classification</b>", body_style),
            Paragraph("<b>Type</b>", body_style),
        ]
    ]

    for doc_id, date, classification, doc_type in docs_info:
        docs_data.append(
            [
                Paragraph(doc_link(doc_id, doc_id), link_style),
                Paragraph(date, body_style),
                Paragraph(classification, body_style),
                Paragraph(doc_type, body_style),
            ]
        )

    docs_table = Table(docs_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    docs_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ]
        )
    )
    story.append(Spacer(1, 10))
    story.append(docs_table)

    # Conclusions
    story.append(Paragraph("Conclusions", heading_style))

    story.append(Paragraph("What the Documents Prove", subheading_style))
    conclusions = [
        "<b>Credit was intentionally blocked</b> - The US used its influence at the World Bank, "
        "IMF, and Inter-American Development Bank to cut off loans to Chile.",
        "<b>Strikes were funded</b> - The CIA financed labor disruptions that damaged the economy "
        "and created public discontent.",
        "<b>Copper revenue was targeted</b> - The US supported legal actions by Kennecott to block "
        "Chilean copper exports in European courts, hitting Chile's main source of foreign currency.",
        "<b>This was coordinated policy</b> - The 40 Committee (NSC covert operations group) "
        "approved these actions at the highest levels of government.",
    ]
    for conclusion in conclusions:
        story.append(Paragraph(f"• {conclusion}", body_style))

    story.append(Paragraph("Balanced Assessment", subheading_style))
    story.append(
        Paragraph(
            "The documents show the US conducted systematic economic warfare against Chile. However, "
            "it is also true that:",
            body_style,
        )
    )

    caveats = [
        "Allende's economic policies (wage increases, price controls, nationalizations) created "
        "genuine economic challenges",
        "Chile faced pre-existing structural economic issues",
        "Inflation had complex domestic causes as well",
    ]
    for caveat in caveats:
        story.append(Paragraph(f"• {caveat}", body_style))

    story.append(Spacer(1, 15))
    story.append(
        Paragraph(
            "<b>The evidence suggests both factors contributed:</b> US intervention demonstrably worsened "
            "economic conditions, but the extent to which each factor contributed is difficult to "
            "quantify precisely. What the documents do prove is that the US <i>intentionally</i> tried "
            'to destabilize Chile\'s economy as a tool of regime change. The argument that Allende\'s '
            "government failed purely due to its own policies is contradicted by these declassified "
            "documents showing coordinated external economic sabotage.",
            body_style,
        )
    )

    # Methodology
    story.append(Paragraph("Methodology", heading_style))
    story.append(
        Paragraph(
            "This analysis was conducted using semantic search (RAG - Retrieval Augmented Generation) "
            "on the Desclasificados archive of declassified CIA documents related to Chile.",
            body_style,
        )
    )

    method_items = [
        "<b>Index:</b> RAG v1.0.0 (created December 18, 2025)",
        "<b>Documents:</b> 5,666 transcribed documents (12,811 text chunks)",
        "<b>Sources:</b> gpt-5-mini-v2.2.0 (4,206 docs) + gpt-5-mini-v2.0.0 (1,460 docs)",
        "<b>Embedding Model:</b> OpenAI text-embedding-3-small",
        "<b>LLM:</b> Claude 3.5 Haiku for answer synthesis",
        "<b>Queries:</b> Two semantic searches with top-15 and top-10 retrieval",
    ]
    for item in method_items:
        story.append(Paragraph(f"• {item}", body_style))

    # Document viewer info
    story.append(Spacer(1, 15))
    story.append(
        Paragraph(
            f'<b>Document Viewer:</b> <a href="{DOCUMENT_VIEWER_BASE_URL}" color="blue">{DOCUMENT_VIEWER_BASE_URL}</a>',
            body_style,
        )
    )
    story.append(
        Paragraph(
            "All document links open in the Desclasificados document viewer where you can browse "
            "the original declassified PDFs.",
            source_style,
        )
    )

    # Footer
    story.append(Spacer(1, 30))
    story.append(
        Paragraph(
            "This report was generated from the Desclasificados project archive. "
            "All cited documents are from declassified US government records.",
            source_style,
        )
    )

    # Build PDF
    doc.build(story)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "us_economic_intervention_chile_1970-1973.pdf"
    create_report(output_file)
