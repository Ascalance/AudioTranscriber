import os
from odf.opendocument import OpenDocumentText
from odf.text import P, H

def export_odt(transcription: str, output_path: str, title: str = "Transcription"):
    doc = OpenDocumentText()
    h = H(outlinelevel=1, text=title)
    doc.text.addElement(h)
    for line in transcription.splitlines():
        p = P(text=line)
        doc.text.addElement(p)
    doc.save(output_path)
