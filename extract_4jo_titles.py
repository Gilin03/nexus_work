with open("temp_4jo_slides.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

with open("temp_4jo_titles.txt", "w", encoding="utf-8") as out:
    for line in lines:
        if line.startswith("=== Slide") or line.startswith("Title/First text:"):
            out.write(line)
