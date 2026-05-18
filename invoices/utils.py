from io import BytesIO
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.conf import settings
import datetime

def generate_invoice_pdf(invoice):
    """
    Generates a professional PDF invoice using ReportLab and returns a Django ContentFile.
    """
    buffer = BytesIO()
    # Use A4 page size
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=15*mm, 
        leftMargin=15*mm, 
        topMargin=15*mm, 
        bottomMargin=15*mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_title = ParagraphStyle(
        name='InvoiceTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor("#2563eb"),
        alignment=2, # Right align
        spaceAfter=12
    )
    
    style_label = ParagraphStyle(
        name='Label',
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        fontWeight='BOLD',
        spaceAfter=2
    )
    
    style_value = ParagraphStyle(
        name='Value',
        fontSize=11,
        textColor=colors.HexColor("#1e293b"),
        fontWeight='NORMAL',
        spaceAfter=8
    )

    style_company = ParagraphStyle(
        name='Company',
        fontSize=14,
        fontWeight='BOLD',
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=2
    )

    # 1. Header: Brand & Invoice Title
    header_data = [
        [
            Paragraph("<b>BATTERIES BAZAAR</b>", style_company),
            Paragraph("INVOICE", style_title)
        ],
        [
            Paragraph("Support: support@batteriesbazaar.com<br/>Phone: +91 98765 43210", styles['Normal']),
            ""
        ]
    ]
    header_table = Table(header_data, colWidths=[110*mm, 70*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=0, spaceAfter=10*mm))

    # 2. Invoice Details Grid
    info_data = [
        [
            Paragraph("<b>INVOICE TO</b>", style_label),
            Paragraph("<b>INVOICE INFO</b>", style_label),
            Paragraph("<b>SELLER INFO</b>", style_label)
        ],
        [
            Paragraph(f"<b>{invoice.customer_name}</b><br/>{invoice.customer_email}<br/>{invoice.order.shipping_address}", style_value),
            Paragraph(f"ID: <b>{invoice.invoice_id}</b><br/>Date: {invoice.invoice_date.strftime('%d %b, %Y')}<br/>Order ID: #{invoice.order.id}", style_value),
            Paragraph(f"<b>{invoice.seller.business_name if invoice.seller else invoice.seller_name}</b><br/>{invoice.seller.user.phone_number if invoice.seller and invoice.seller.user.phone_number else ''}", style_value)
        ],
        [
            "",
            Paragraph("<b>PAYMENT</b>", style_label),
            ""
        ],
        [
            "",
            Paragraph(f"Method: {invoice.payment_method}<br/>Status: <b>{invoice.payment_status}</b>", style_value),
            ""
        ]
    ]
    info_table = Table(info_data, colWidths=[65*mm, 65*mm, 50*mm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10*mm))

    # 3. Items Table
    items_data = [
        ["#", "Product Details", "Quantity", "Unit Price", "Total"]
    ]
    
    # Filter items that belong to this invoice's seller
    relevant_items = invoice.order.items.filter(seller=invoice.seller)
    
    for i, item in enumerate(relevant_items, 1):
        product_title = ""
        product_desc = ""
        if item.product:
            product_title = item.product.name
            product_desc = item.product.description[:100] + "..." if len(item.product.description) > 100 else item.product.description
        elif item.combo_product:
            product_title = f"Combo: {item.combo_product.name}"
            product_desc = item.combo_product.description[:100] + "..." if item.combo_product.description and len(item.combo_product.description) > 100 else (item.combo_product.description or "")
        else:
            product_title = "Product"
            
        product_cell = Paragraph(f"<b>{product_title}</b><br/><font size='8' color='#64748b'>{product_desc}</font>", styles['Normal'])
        
        items_data.append([
            str(i),
            product_cell,
            str(item.quantity),
            f"Rs. {item.price}",
            f"Rs. {item.total_amount}"
        ])

    items_table = Table(items_data, colWidths=[10*mm, 90*mm, 20*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        # Header Styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('ALIGN', (2, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Row Styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#1e293b")),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        
        # Border
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10*mm))

    # 4. Summary Table
    # In this system, total_amount in Invoice is the sum of (price * quantity) for the seller's items
    subtotal = sum(item.total_amount for item in relevant_items)
    tax = subtotal * Decimal('0.18')
    grand_total = subtotal + tax

    summary_data = [
        ["", "Subtotal", f"Rs. {subtotal}"],
        ["", "Tax / GST (18%)", f"Rs. {tax:.2f}"],
        ["", "Grand Total", f"Rs. {grand_total:.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[100*mm, 40*mm, 40*mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (1, 2), (2, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (2, 2), 11),
        ('TEXTCOLOR', (1, 0), (2, 2), colors.HexColor("#1e293b")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        # Total line highlighting
        ('LINEABOVE', (1, 2), (2, 2), 1, colors.HexColor("#2563eb")),
        ('TOPPADDING', (1, 2), (2, 2), 8),
    ]))
    elements.append(summary_table)
    
    # 5. Footer Section
    elements.append(Spacer(1, 30*mm))
    footer_text = """
    <b>Thank you for choosing Batteries Bazaar!</b><br/>
    Please note: This is a computer-generated invoice. No signature required.<br/>
    For any support or warranty queries, contact us at <b>support@batteriesbazaar.com</b>.
    """
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f1f5f9"), spaceAfter=5*mm))
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build the PDF
    doc.build(elements)
    
    pdf_value = buffer.getvalue()
    buffer.close()
    
    return ContentFile(pdf_value, name=f"{invoice.invoice_id}.pdf")

def send_invoice_email(invoice):
    """
    Generates the invoice PDF and sends it to the customer via email.
    """
    try:
        # Generate PDF
        pdf_file = generate_invoice_pdf(invoice)
        
        subject = f"Invoice for your Order #{invoice.order.id} - {invoice.invoice_id}"
        body = f"""
Dear {invoice.customer_name},

Thank you for your purchase from Batteries Bazaar!

Please find attached the professional invoice for your recent order.

Order Details:
- Order ID: #{invoice.order.id}
- Invoice ID: {invoice.invoice_id}
- Date: {invoice.invoice_date.strftime('%d %b, %Y')}
- Total Amount: Rs. {invoice.total_amount}

If you have any questions or need support, please reach out to us.

Best regards,
The Batteries Bazaar Team
"""
        
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[invoice.customer_email],
        )
        
        # Attach the PDF
        email.attach(f"{invoice.invoice_id}.pdf", pdf_file.read(), 'application/pdf')
        
        # Send the email
        email.send()
        return True
    except Exception as e:
        print(f"Error sending invoice email: {e}")
        return False
