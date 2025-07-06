import os
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def export_pdf(transcription: str, output_path: str, title: str = "Transcription"):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 72, title)
    y = height - 100
    for line in transcription.splitlines():
        if y < 72:
            c.showPage()
            y = height - 72
        c.drawString(72, y, line)
        y -= 18
    c.save()
