from pathlib import Path

from pypdf import PdfReader


PDFS = [
    Path(r"C:\Users\Lenovo\Desktop\YAZILIM MÜHENDİSLİĞİ\Otomasyon Projesi - CI\CI_Interface_Contract.pdf"),
    Path(r"C:\Users\Lenovo\Desktop\YAZILIM MÜHENDİSLİĞİ\Otomasyon Projesi - CI\CI_Implementasyon_Rehberi.pdf"),
]

OUT_DIR = Path(r"C:\Users\Lenovo\Desktop\ci_automation_system\repo-manager\integration\doc_extract")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for pdf in PDFS:
        reader = PdfReader(str(pdf))
        out_file = OUT_DIR / f"{pdf.stem}.txt"
        with out_file.open("w", encoding="utf-8") as handle:
            handle.write(f"FILE: {pdf.name}\nPAGES: {len(reader.pages)}\n\n")
            for index, page in enumerate(reader.pages, start=1):
                handle.write(f"===== PAGE {index} =====\n")
                handle.write(page.extract_text() or "")
                handle.write("\n\n")
        print(f"extracted {pdf.name} -> {out_file}")


if __name__ == "__main__":
    main()
