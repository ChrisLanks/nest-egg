"""Input sanitization service for preventing XSS and injection attacks."""

import re
import html
from typing import Optional


class InputSanitizationService:
    """Service for sanitizing user input to prevent XSS and other attacks."""

    # Dangerous HTML tags that should always be stripped
    DANGEROUS_TAGS = [
        "script",
        "iframe",
        "object",
        "embed",
        "applet",
        "meta",
        "link",
        "style",
        "form",
        "input",
        "button",
        "textarea",
        "select",
    ]

    # Dangerous attributes that should be removed
    DANGEROUS_ATTRS = [
        "onclick",
        "onload",
        "onerror",
        "onmouseover",
        "onmouseout",
        "onfocus",
        "onblur",
        "onchange",
        "onsubmit",
        "javascript:",
    ]

    @staticmethod
    def sanitize_html(text: Optional[str], allow_basic_formatting: bool = False) -> Optional[str]:
        """
        Sanitize text by stripping all HTML tags and escaping special characters.

        For a personal finance application, there is no legitimate need for HTML
        in user input. This method always strips tags and escapes to prevent XSS.

        Args:
            text: The text to sanitize
            allow_basic_formatting: Deprecated, ignored. Always strips all HTML.

        Returns:
            Sanitized text with all HTML removed and special characters escaped
        """
        if not text:
            return text

        # Strip ALL HTML tags (allowlist approach — no tag is permitted)
        text = re.sub(r"<[^>]*>", "", text)

        # Escape angle brackets and ampersands as defense-in-depth.
        # quote=False preserves apostrophes/quotes in names (e.g. "Jane's Household")
        # which is safe because all tags are already stripped above.
        text = html.escape(text, quote=False)

        return text

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem operations
        """
        # Remove path separators
        filename = filename.replace("/", "_").replace("\\", "_")

        # Remove null bytes
        filename = filename.replace("\x00", "")

        # Remove leading dots (hidden files)
        filename = filename.lstrip(".")

        # Only allow alphanumeric, dash, underscore, and dot
        filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[:250] + ("." + ext if ext else "")

        return filename

    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """
        Sanitize search query to prevent SQL injection and other attacks.

        Note: This is defense-in-depth. SQLAlchemy ORM already prevents SQL injection,
        but this adds an extra layer of protection.

        Args:
            query: Search query string

        Returns:
            Sanitized query string
        """
        if not query:
            return ""

        # Remove SQL comment indicators
        query = query.replace("--", "").replace("/*", "").replace("*/", "")

        # Remove semicolons (SQL statement terminators)
        query = query.replace(";", "")

        # Remove null bytes
        query = query.replace("\x00", "")

        # Limit length to prevent DoS
        if len(query) > 500:
            query = query[:500]

        return query.strip()

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if valid email format
        """
        # Basic email regex (Pydantic EmailStr is better, this is backup)
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def sanitize_url(url: str) -> Optional[str]:
        """
        Sanitize URL to prevent javascript: and data: URI attacks.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL or None if dangerous
        """
        if not url:
            return None

        url = url.strip()

        # Block dangerous protocols
        dangerous_protocols = ["javascript:", "data:", "vbscript:", "file:"]
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                return None

        # Only allow http, https, and mailto
        if not re.match(r"^(https?|mailto):", url, re.IGNORECASE):
            # If no protocol, assume https
            if not url.startswith("//"):
                url = "https://" + url

        return url

    @staticmethod
    def sanitize_json_string(text: str) -> str:
        """
        Sanitize JSON string values to prevent injection.

        Args:
            text: String value from JSON

        Returns:
            Sanitized string
        """
        # Remove control characters
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

        # Escape backslashes and quotes
        text = text.replace("\\", "\\\\").replace('"', '\\"')

        return text

    @staticmethod
    def strip_control_characters(text: str) -> str:
        """
        Remove control characters from text.

        Args:
            text: Input text

        Returns:
            Text without control characters
        """
        # Remove all control characters except newline and tab
        return re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)


# Create singleton instance
input_sanitization_service = InputSanitizationService()
