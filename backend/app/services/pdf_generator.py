from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

PDF_DIR = os.path.join("app", "static")
if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

PDF_PATH = os.path.join(PDF_DIR, "latest_notes.pdf")

def generate_daily_pdf(articles):
    """
    Generates a generic PDF containing the summarized news.
    articles should be a list of dicts: [{"title": "...", "summary": "..."}, ...]
    """
    doc = SimpleDocTemplate(PDF_PATH, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = styles['Heading1']
    content_style = styles['BodyText']
    
    Story = []
    
    # Header
    Story.append(Paragraph("<b>Daily Current Affairs Notes - SSC</b>", title_style))
    Story.append(Spacer(1, 20))
    
    for article in articles:
        # Title
        Story.append(Paragraph(f"<b>{article['title']}</b>", styles['Heading2']))
        Story.append(Spacer(1, 5))
        
        # Summary (replacing newlines with html breaks for reportlab)
        formatted_summary = article['summary'].replace('\n', '<br />')
        Story.append(Paragraph(formatted_summary, content_style))
        Story.append(Spacer(1, 15))
        
    try:
        doc.build(Story)
        print(f"Generated PDF at {PDF_PATH}")
    except Exception as e:
        print(f"Failed to generate PDF: {e}")
