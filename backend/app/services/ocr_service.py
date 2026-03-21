"""
Receipt OCR service.

Uses pytesseract if available, otherwise attempts basic regex extraction
from PDF text or returns empty data. Designed to be best-effort — failures
never block the upload flow.
"""
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)


class OcrService:

    def extract_from_image(self, file_bytes: bytes, content_type: str) -> dict:
        """
        Attempt to extract receipt data from an image or PDF.
        Returns dict with keys: merchant, amount, date, raw_text, confidence
        All values may be None if extraction fails.
        """
        raw_text = self._get_text(file_bytes, content_type)
        if not raw_text:
            return {
                "merchant": None,
                "amount": None,
                "date": None,
                "raw_text": None,
                "confidence": 0.0,
            }

        return {
            "merchant": self._extract_merchant(raw_text),
            "amount": self._extract_amount(raw_text),
            "date": self._extract_date(raw_text),
            "raw_text": raw_text[:500],  # truncate for storage
            "confidence": 0.5 if raw_text else 0.0,
        }

    def _get_text(self, file_bytes: bytes, content_type: str) -> Optional[str]:
        """Try to extract text using pytesseract or pdfplumber."""
        if content_type == "application/pdf":
            try:
                import io

                import pdfplumber

                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    return "\n".join(
                        page.extract_text() or "" for page in pdf.pages[:2]
                    )
            except ImportError:
                pass
            except Exception as e:
                logger.debug("PDF text extraction failed: %s", e)

        if content_type.startswith("image/"):
            try:
                import io

                import pytesseract
                from PIL import Image

                img = Image.open(io.BytesIO(file_bytes))
                return pytesseract.image_to_string(img)
            except ImportError:
                pass
            except Exception as e:
                logger.debug("OCR failed: %s", e)

        return None

    def _extract_amount(self, text: str) -> Optional[str]:
        """Find the largest dollar amount in text (likely the total)."""
        amounts = re.findall(r"\$?\s*(\d{1,6}[.,]\d{2})", text)
        if not amounts:
            return None
        # Return the largest amount as the likely total
        parsed = []
        for a in amounts:
            try:
                parsed.append(Decimal(a.replace(",", "")))
            except InvalidOperation:
                pass
        return str(max(parsed)) if parsed else None

    def _extract_merchant(self, text: str) -> Optional[str]:
        """Try to extract merchant name from first non-empty line."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # First substantial line is often the merchant name
        for line in lines[:5]:
            if len(line) > 3 and not re.match(r"^[\d$#\-]+$", line):
                return line[:100]
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Find a date pattern in text."""
        patterns = [
            r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None


ocr_service = OcrService()
