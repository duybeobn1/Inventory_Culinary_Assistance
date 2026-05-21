import os
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def extract_all_epubs(directory):
    master_text = ""
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".epub"):
            print(f"Reading: {filename}...")
            book = epub.read_epub(os.path.join(directory, filename))
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                master_text += f"\n--- Source: {filename} ---\n"
                master_text += soup.get_text() + "\n"
    return master_text

if __name__ == "__main__":
    all_theory = extract_all_epubs("./books")
    with open("raw_master_theory.txt", "w", encoding="utf-8") as f:
        f.write(all_theory)
    print(f"Extracted {len(all_theory)} characters to raw_master_theory.txt")
