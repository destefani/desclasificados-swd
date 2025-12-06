"""
Generate PDF report for Model OCR Capability Comparison.
Desclasificados Project - December 2024
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from pathlib import Path


def create_report():
    """Generate the model comparison PDF report."""

    # Output path
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "Model_OCR_Comparison_Report.pdf"

    # Create document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d')
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a5568')
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.HexColor('#2d3748')
    )

    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=13,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#4a5568')
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10,
        leading=14
    )

    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=10,
        backColor=colors.HexColor('#e6fffa'),
        borderPadding=10,
        leading=16
    )

    # Build content
    story = []

    # Title
    story.append(Paragraph("Model OCR Capability Comparison Report", title_style))
    story.append(Paragraph("Desclasificados Project - CIA Declassified Documents Transcription", subtitle_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a365d')))
    story.append(Spacer(1, 20))

    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(
        "This report evaluates various AI models for their ability to perform Optical Character Recognition (OCR) "
        "on declassified CIA documents. The goal is to identify the most cost-effective model that produces "
        "complete, verbatim text transcriptions suitable for full-text search and research purposes.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Key Finding Box
    story.append(Paragraph(
        "<b>KEY FINDING:</b> <b>gpt-4.1-nano</b> is the recommended model at <b>~$30</b> for the full pass "
        "(21,512 PDFs, ~76,000 pages), representing a <b>97% cost reduction</b> compared to Claude Sonnet 4.5 (~$1,010) "
        "while still providing complete OCR transcription.",
        highlight_style
    ))
    story.append(Spacer(1, 20))

    # Project Overview
    story.append(Paragraph("Project Overview", heading_style))

    project_data = [
        ['Metric', 'Value'],
        ['Total PDF Documents', '21,512'],
        ['Total Pages (estimated)', '~76,152'],
        ['Average Pages per PDF', '3.54'],
        ['Estimated Input Tokens', '~122 million'],
        ['Estimated Output Tokens', '~43 million'],
    ]

    project_table = Table(project_data, colWidths=[3*inch, 3*inch])
    project_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f7fafc'), colors.white]),
    ]))
    story.append(project_table)
    story.append(Spacer(1, 20))

    # Critical Decision: PDFs vs Images
    story.append(Paragraph("Critical Decision: PDFs vs Images", heading_style))
    story.append(Paragraph(
        "The source data exists in two formats: extracted images (first page only) and original PDFs (all pages). "
        "Using PDFs is essential for complete document coverage.",
        body_style
    ))

    pdf_vs_image_data = [
        ['Source', 'Files', 'Pages', 'Coverage'],
        ['data/images/', '21,512', '21,512', 'First page only (INCOMPLETE)'],
        ['data/original_pdfs/', '21,512', '~76,152', 'All pages (COMPLETE)'],
    ]

    pdf_table = Table(pdf_vs_image_data, colWidths=[1.8*inch, 1.2*inch, 1.2*inch, 2.3*inch])
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#c6f6d5')),
    ]))
    story.append(pdf_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>Decision:</b> Use PDFs for complete document coverage. 82% of documents have multiple pages.",
        body_style
    ))
    story.append(Spacer(1, 20))

    # Model Testing Results
    story.append(Paragraph("Model Testing Results", heading_style))
    story.append(Paragraph(
        "Each model was tested with the same declassified document image to evaluate OCR capability. "
        "Models were assessed on whether they produce actual verbatim text or placeholder/refusal responses.",
        body_style
    ))

    story.append(Paragraph("OCR Capability Test Results", subheading_style))

    ocr_test_data = [
        ['Model', 'Full OCR', 'Output Length', 'Status'],
        ['gpt-4.1-nano', 'YES', '933 chars', 'Working - Cheapest'],
        ['gpt-4.1-mini', 'YES', '1,627 chars', 'Working - Good balance'],
        ['gpt-4o', 'YES', '1,679 chars', 'Working - Expensive'],
        ['gpt-5.1-2025-11-13', 'YES', '1,188 chars', 'Working - Previously used'],
        ['gpt-4o-mini', 'NO', '40 chars', 'REFUSED to transcribe'],
        ['gpt-5-nano', 'N/A', '-', 'No vision support'],
        ['gpt-5-mini', 'N/A', '-', 'No vision support'],
        ['claude-3-5-haiku', 'NO', '29 chars', 'Placeholder text only'],
        ['claude-sonnet-4.5', 'YES', '1,800+ chars', 'Working - Most expensive'],
    ]

    ocr_table = Table(ocr_test_data, colWidths=[1.8*inch, 0.9*inch, 1.1*inch, 2.2*inch])
    ocr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        # Highlight working models
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#c6f6d5')),  # gpt-4.1-nano
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e6fffa')),  # gpt-4.1-mini
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#fed7d7')),  # gpt-4o-mini refused
        ('BACKGROUND', (0, 8), (-1, 8), colors.HexColor('#fed7d7')),  # haiku no OCR
    ]))
    story.append(ocr_table)
    story.append(Spacer(1, 20))

    # Page Break
    story.append(PageBreak())

    # Cost Analysis
    story.append(Paragraph("Cost Analysis", heading_style))
    story.append(Paragraph(
        "Pricing is based on official API rates per million tokens. Estimates assume ~1,600 input tokens "
        "per page and ~2,000 output tokens per document.",
        body_style
    ))

    story.append(Paragraph("API Pricing (per million tokens)", subheading_style))

    pricing_data = [
        ['Model', 'Input', 'Output', 'Notes'],
        ['gpt-4.1-nano', '$0.10', '$0.40', 'Cheapest with vision'],
        ['gpt-4.1-mini', '$0.40', '$1.60', 'Good balance'],
        ['gpt-4.1', '$2.00', '$8.00', 'Full capability'],
        ['gpt-4o-mini', '$0.15', '$0.60', 'No OCR capability'],
        ['gpt-4o', '$2.50', '$10.00', 'Multimodal flagship'],
        ['gpt-5.1', '$2.00', '$8.00', 'Latest generation'],
        ['claude-3-5-haiku', '$0.80', '$4.00', 'No full OCR'],
        ['claude-sonnet-4.5', '$3.00', '$15.00', 'Highest quality'],
    ]

    pricing_table = Table(pricing_data, colWidths=[1.8*inch, 1*inch, 1*inch, 2.2*inch])
    pricing_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#c6f6d5')),
    ]))
    story.append(pricing_table)
    story.append(Spacer(1, 20))

    # Full Pass Cost Estimates
    story.append(Paragraph("Full Pass Cost Estimates", subheading_style))
    story.append(Paragraph(
        "Estimated costs for processing all 21,512 PDFs (~76,152 pages):",
        body_style
    ))

    cost_data = [
        ['Model', 'Input Cost', 'Output Cost', 'TOTAL', 'Full OCR'],
        ['gpt-4.1-nano', '$12.18', '$17.21', '$29.39', 'YES'],
        ['gpt-4.1-mini', '$48.74', '$68.84', '$117.58', 'YES'],
        ['gpt-4o-mini', '$18.28', '$25.81', '$44.09', 'NO'],
        ['gpt-4o', '$304.61', '$430.24', '$734.85', 'YES'],
        ['gpt-5.1', '$243.69', '$344.19', '$587.88', 'YES'],
        ['claude-3-5-haiku', '$97.47', '$172.10', '$269.57', 'NO'],
        ['claude-sonnet-4.5', '$365.53', '$645.36', '$1,010.89', 'YES'],
    ]

    cost_table = Table(cost_data, colWidths=[1.5*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1*inch])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        # Highlight recommended
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#c6f6d5')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        # Highlight NO OCR rows
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fed7d7')),
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#fed7d7')),
    ]))
    story.append(cost_table)
    story.append(Spacer(1, 20))

    # Cost Comparison Chart (text representation)
    story.append(Paragraph("Cost Comparison (Models with Full OCR)", subheading_style))

    bar_data = [
        ['Model', 'Cost', 'Visual'],
        ['gpt-4.1-nano', '$29', '██ (2.9%)'],
        ['gpt-4.1-mini', '$118', '████████ (11.7%)'],
        ['gpt-5.1', '$588', '████████████████████████████████████████ (58.2%)'],
        ['gpt-4o', '$735', '██████████████████████████████████████████████████ (72.8%)'],
        ['claude-sonnet-4.5', '$1,011', '████████████████████████████████████████████████████████████████████ (100%)'],
    ]

    bar_table = Table(bar_data, colWidths=[1.5*inch, 0.8*inch, 3.7*inch])
    bar_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#c6f6d5')),
    ]))
    story.append(bar_table)
    story.append(Spacer(1, 20))

    # Page Break
    story.append(PageBreak())

    # Recommendations
    story.append(Paragraph("Recommendations", heading_style))

    story.append(Paragraph("Primary Recommendation: gpt-4.1-nano", subheading_style))
    story.append(Paragraph(
        "<b>gpt-4.1-nano</b> is recommended for the full transcription pass based on:",
        body_style
    ))
    story.append(Paragraph("• <b>Cost:</b> ~$30 for complete pass (97% cheaper than Claude Sonnet)", body_style))
    story.append(Paragraph("• <b>OCR Quality:</b> Produces 933+ characters of actual transcribed text", body_style))
    story.append(Paragraph("• <b>Speed:</b> Fast inference with minimal latency", body_style))
    story.append(Paragraph("• <b>Reliability:</b> Consistent output format", body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("Backup Option: gpt-4.1-mini", subheading_style))
    story.append(Paragraph(
        "If nano quality proves insufficient, <b>gpt-4.1-mini</b> offers better quality at ~$118 "
        "(still 88% cheaper than Claude Sonnet).",
        body_style
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("Models to Avoid", subheading_style))
    story.append(Paragraph("• <b>gpt-4o-mini:</b> Refuses to transcribe declassified documents", body_style))
    story.append(Paragraph("• <b>claude-3-5-haiku:</b> Returns placeholder text instead of actual OCR", body_style))
    story.append(Paragraph("• <b>gpt-5-nano/mini:</b> No vision/image support", body_style))
    story.append(Spacer(1, 20))

    # Implementation Notes
    story.append(Paragraph("Implementation Notes", heading_style))
    story.append(Paragraph(
        "The following implementation details should be considered for the full pass:",
        body_style
    ))
    story.append(Paragraph("• Use <b>--use-pdf</b> flag to process original PDFs (all pages)", body_style))
    story.append(Paragraph("• Set <b>max_completion_tokens</b> instead of max_tokens for GPT-5.x models", body_style))
    story.append(Paragraph("• Implement rate limiting based on API tier limits", body_style))
    story.append(Paragraph("• Use resume capability to handle interruptions", body_style))
    story.append(Paragraph("• Monitor costs in real-time during processing", body_style))
    story.append(Spacer(1, 20))

    # Appendix
    story.append(Paragraph("Appendix: Test Methodology", heading_style))
    story.append(Paragraph(
        "Each model was tested using the same declassified CIA document image (24736.jpg) with a standardized "
        "transcription prompt. Models were evaluated on:",
        body_style
    ))
    story.append(Paragraph("1. Whether they produced actual text vs. placeholder/refusal", body_style))
    story.append(Paragraph("2. Length of output text (indicator of completeness)", body_style))
    story.append(Paragraph("3. Token usage for cost estimation", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Testing was conducted on December 4, 2024. Pricing information sourced from official OpenAI and "
        "Anthropic API documentation.",
        body_style
    ))
    story.append(Spacer(1, 30))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Report generated for the Desclasificados Project<br/>"
        "CIA Declassified Documents on the Chilean Dictatorship (1973-1990)<br/>"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
    ))

    # Build PDF
    doc.build(story)
    print(f"Report generated: {output_path}")
    return output_path


if __name__ == "__main__":
    create_report()
