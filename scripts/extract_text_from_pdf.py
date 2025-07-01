import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images (one image per page)
pdf_path = "scripts/Barak Rosenshine Poster.pdf"
images = convert_from_path(pdf_path)

# Perform OCR on each page image and collect text
ocr_text = []
for i, img in enumerate(images):
    text = pytesseract.image_to_string(img)
    ocr_text.append(f"--- Page {i + 1} ---\n{text.strip()}")

# Combine all pages' text into one
full_text = "\n\n".join(ocr_text)
print(full_text)
