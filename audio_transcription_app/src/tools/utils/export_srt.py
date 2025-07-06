import os
from typing import List

def export_srt(transcription: str, output_path: str, timestamps: List[str] = None):
    """
    transcription: plain text, one line per subtitle
    timestamps: list of timestamp strings (optional, must match number of lines)
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        lines = transcription.splitlines()
        for i, line in enumerate(lines):
            f.write(f"{i+1}\n")
            if timestamps and i < len(timestamps):
                f.write(f"{timestamps[i]}\n")
            else:
                f.write("00:00:00,000 --> 00:00:05,000\n")
            f.write(f"{line}\n\n")
