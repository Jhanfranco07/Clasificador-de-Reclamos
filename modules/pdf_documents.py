"""Extracción local de texto PDF para revisión administrativa."""
import io
import os
import re
import unicodedata

from pypdf import PdfReader, apply_configuration

PDF_MAX_BYTES = int(os.getenv("DOCUMENT_PDF_MAX_BYTES", str(4 * 1024 * 1024)))
PDF_MAX_PAGES = int(os.getenv("DOCUMENT_PDF_MAX_PAGES", "25"))
PDF_MAX_TEXT = 100_000


class InvalidDocumentPdf(ValueError):
    pass


def extract_pdf_text(data: bytes) -> str:
    with apply_configuration(
        maximum_declared_stream_length=PDF_MAX_BYTES,
        array_based_stream_maximum_output_length=1_000_000,
        zlib_maximum_output_length=1_000_000,
        lzw_maximum_output_length=1_000_000,
        brotli_maximum_output_length=1_000_000,
        run_length_maximum_output_length=1_000_000,
        stream_decoding_work_maximum_length=2_000_000,
        stream_parsing_work_maximum_count=100_000,
        page_tree_maximum_entries=PDF_MAX_PAGES * 4,
        xform_maximum_invocations_per_extraction=100,
        jbig2dec_binary=None,
    ):
        return _extract_pdf_text(data)


def _extract_pdf_text(data: bytes) -> str:
    if len(data) > PDF_MAX_BYTES:
        raise InvalidDocumentPdf("El PDF supera el tamaño permitido.")
    if not re.match(rb"%PDF-(?:1[.][0-7]|2[.]0)[\r\n]", data):
        raise InvalidDocumentPdf("El archivo no tiene una cabecera PDF válida.")
    try:
        pdf = PdfReader(io.BytesIO(data), strict=True, xref_stream_maximum_entries=20_000)
        if pdf.is_encrypted:
            raise InvalidDocumentPdf("El PDF está protegido con contraseña.")
        if len(pdf.pages) > PDF_MAX_PAGES:
            raise InvalidDocumentPdf("El PDF supera el límite de páginas.")
        texts = []
        size = 0
        for page in pdf.pages:
            stream = page.get_contents()
            if stream and len(stream.get_data()) > 512_000:
                raise InvalidDocumentPdf("Una página supera el límite de contenido procesable.")
            page_text = unicodedata.normalize("NFC", page.extract_text() or "")
            page_text = "".join(
                char for char in page_text
                if char in "\n\t" or not unicodedata.category(char).startswith("C")
            ).strip()
            size += len(page_text) + 2
            if size > PDF_MAX_TEXT:
                raise InvalidDocumentPdf("El texto del PDF supera el límite permitido.")
            texts.append(page_text)
    except InvalidDocumentPdf:
        raise
    except Exception as exc:
        raise InvalidDocumentPdf("El PDF está dañado o su formato no es compatible.") from exc
    text = "\n\n".join(filter(None, texts))
    if sum(char.isalnum() for char in text) < 20:
        raise InvalidDocumentPdf("El PDF no contiene suficiente texto legible. Los escaneos requieren una versión con texto.")
    return text
