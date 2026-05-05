from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.core.files.base import ContentFile
import datetime

def generate_invoice_pdf(invoice):
    """
    Generates a PDF invoice using ReportLab and returns a Django ContentFile.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=2))
    
    # Title
    elements.append(Paragraph(f"<b>INVOICE</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Header Information
    header_data = [
        [f"Invoice ID: {invoice.invoice_id}", f"Date: {invoice.invoice_date.strftime('%Y-%m-%d')}"],
        [f"Order ID: #{invoice.order.id}", f"Payment Method: {invoice.payment_method}"],
        [f"Status: {invoice.payment_status}", ""]
    ]
    
    header_table = Table(header_data, colWidths=[230, 230])
    header_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 24))
    
    # Customer & Seller Details
    details_data = [
        ["Billed To:", "From Seller:"],
        [invoice.customer_name, invoice.seller_name],
        [invoice.customer_email, ""]
    ]
    details_table = Table(details_data, colWidths=[230, 230])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 24))
    
    # Amounts
    amounts_data = [
        ["Description", "Amount"],
        ["Total Amount", f"Rs. {invoice.total_amount}"],
        ["Admin Commission", f"Rs. {invoice.commission_amount}"],
        ["Seller Earnings", f"Rs. {invoice.seller_amount}"],
    ]
    amounts_table = Table(amounts_data, colWidths=[300, 160])
    amounts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(amounts_table)
    
    # Build the PDF
    doc.build(elements)
    
    pdf_value = buffer.getvalue()
    buffer.close()
    
    return ContentFile(pdf_value, name=f"{invoice.invoice_id}.pdf")
