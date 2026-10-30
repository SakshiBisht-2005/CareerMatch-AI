from pathlib import Path
import os

import pymupdf   


# Common Windows installation location for Tesseract.
TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR"
)

if TESSERACT_PATH.exists():
    os.environ["PATH"] = (
        str(TESSERACT_PATH)
        + os.pathsep
        + os.environ.get("PATH", "")
    )


def extract_pdf_text(pdf_path):
    """
    Extract text from a PDF.

    Digital pages:
        Extract text directly using PyMuPDF.

    Scanned pages:
        Use Tesseract OCR through PyMuPDF.

    Returns:
        A dictionary containing extracted text and PDF information.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("The uploaded file is not a PDF.")

    if pdf_path.stat().st_size == 0:
        raise ValueError("The uploaded PDF is empty.")

    extracted_pages = []
    ocr_pages = []
    digital_pages = []

    try:
        with pymupdf.open(pdf_path) as pdf:

            if pdf.is_encrypted:
                raise ValueError(
                    "This PDF is password-protected. "
                    "Please upload an unlocked PDF."
                )

            if len(pdf) == 0:
                raise ValueError("The PDF contains no pages.")

            for page_number, page in enumerate(pdf, start=1):

                # First attempt: normal digital text extraction.
                page_text = page.get_text("text").strip()

                if page_text:
                    digital_pages.append(page_number)

                else:
                    # Second attempt: OCR for scanned pages.
                    try:
                        text_page = page.get_textpage_ocr(
                            language="eng",
                            dpi=250,
                            full=True,
                        )

                        page_text = page.get_text(
                            "text",
                            textpage=text_page,
                        ).strip()

                        if page_text:
                            ocr_pages.append(page_number)

                    except Exception as exc:
                        raise RuntimeError(
                            f"OCR failed on PDF page "
                            f"{page_number}. Check Tesseract "
                            f"installation and English language data."
                        ) from exc

                if page_text:
                    extracted_pages.append(
                        f"--- Page {page_number} ---\n"
                        f"{page_text}"
                    )

            full_text = "\n\n".join(
                extracted_pages
            ).strip()

            if not full_text:
                raise ValueError(
                    "No readable text was found in this PDF. "
                    "The document may be blank, damaged, or "
                    "too difficult for OCR to recognize."
                )

            return {
                "text": full_text,
                "total_pages": len(pdf),
                "digital_pages": digital_pages,
                "ocr_pages": ocr_pages,
                "extracted_pages": len(extracted_pages),
            }

    except pymupdf.FileDataError as exc:
        raise ValueError(
            "The PDF is damaged or has an unsupported format."
        ) from exc

    except pymupdf.FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Could not open PDF: {pdf_path}"
        ) from exc