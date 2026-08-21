"""Safe, page-aware extraction for uploaded reports.

This module only extracts text already present in a file. It never performs
clinical interpretation, OCR, embedding, or inference.
"""

import hashlib
from datetime import datetime, timezone

import fitz

from .extensions import db
from .models import ReportExtraction, ReportPage


class ExtractionError(Exception):
    """A user-safe extraction failure."""


def content_hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def is_readable_pdf(blob: bytes) -> bool:
    """Verify a PDF can be opened before storing it as one."""
    try:
        document = fitz.open(stream=blob, filetype="pdf")
        document.close()
        return True
    except (fitz.FileDataError, RuntimeError, ValueError):
        return False


def extract_report(report, blob: bytes):
    """Create pages and an explicit extraction result for an owned report."""
    parser = {"application/pdf": "pymupdf", "text/plain": "utf-8"}.get(
        report.content_type, "ocr-not-configured"
    )
    extraction = ReportExtraction(
        report_id=report.id,
        parser=parser,
        status="processing",
        content_hash=content_hash(blob),
    )
    db.session.add(extraction)
    db.session.flush()

    try:
        if report.content_type == "application/pdf":
            pages = _extract_pdf(blob)
        elif report.content_type == "text/plain":
            pages = [_extract_text(blob)]
        else:
            extraction.status = "needs_ocr"
            extraction.error = "Image report requires OCR before text extraction."
            extraction.extracted_at = datetime.now(timezone.utc)
            db.session.flush()
            return extraction

        extraction.page_count = len(pages)
        for number, text in enumerate(pages, start=1):
            db.session.add(ReportPage(
                report_id=report.id,
                page_number=number,
                text=text,
                character_count=len(text),
            ))

        if not any(text.strip() for text in pages):
            raise ExtractionError(
                "No extractable text found in this report. It may be scanned and requires OCR."
            )

        extraction.status = "completed"
        extraction.extracted_text = "\n\n".join(
            f"--- Page {number} ---\n{text}" for number, text in enumerate(pages, start=1)
        )
    except ExtractionError as error:
        extraction.status = "failed"
        extraction.error = str(error)
        extraction.extracted_text = None
    extraction.extracted_at = datetime.now(timezone.utc)
    db.session.flush()
    return extraction


def _extract_pdf(blob: bytes) -> list[str]:
    try:
        document = fitz.open(stream=blob, filetype="pdf")
    except (fitz.FileDataError, RuntimeError, ValueError) as error:
        raise ExtractionError("Unable to read this PDF.") from error

    try:
        if document.page_count == 0:
            raise ExtractionError("This PDF contains no pages.")
        return [page.get_text("text") for page in document]
    except (RuntimeError, ValueError) as error:
        raise ExtractionError("Unable to extract text from this PDF.") from error
    finally:
        document.close()


def _extract_text(blob: bytes) -> str:
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExtractionError("This text report is not valid UTF-8.") from error
