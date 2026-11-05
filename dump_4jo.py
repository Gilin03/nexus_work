import pptx
import os

pptx_path = r"C:\Users\user\Downloads\4조_NEXUS_WORK.pptx"
prs = pptx.Presentation(pptx_path)

print(f"Total slides: {len(prs.slides)}")

output = []
for idx, slide in enumerate(prs.slides, 1):
    texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                t = p.text.strip()
                if t and t not in texts:
                    texts.append(t)
    title = texts[0] if texts else "(No text)"
    output.append(f"=== Slide {idx} ===")
    output.append(f"Title/First text: {title}")
    output.append("All texts:")
    for t in texts:
        output.append(f"  - {t}")
    output.append("")

with open("temp_4jo_slides.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Dumped to temp_4jo_slides.txt")
