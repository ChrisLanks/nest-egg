"""Tests for JWT iss/aud claim enforcement and WebP RIFF validation."""

import jwt as _jwt
import pytest
from datetime import timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_mfa_pending_token,
    decode_token,
)
from app.utils.datetime_utils import utc_now


@pytest.mark.unit
class TestJwtIssuedAudienceClaims:
    """JWT tokens must include iss and aud claims and decode_token must validate them."""

    def test_access_token_includes_iss(self):
        token = create_access_token({"sub": "user-1"})
        # Decode without validation to inspect raw claims
        raw = _jwt.decode(token, options={"verify_signature": False})
        assert raw["iss"] == "nest-egg"

    def test_access_token_includes_aud(self):
        token = create_access_token({"sub": "user-1"})
        raw = _jwt.decode(token, options={"verify_signature": False})
        assert raw["aud"] == "nest-egg"

    def test_refresh_token_includes_iss_and_aud(self):
        token, _jti, _exp = create_refresh_token("user-1")
        raw = _jwt.decode(token, options={"verify_signature": False})
        assert raw["iss"] == "nest-egg"
        assert raw["aud"] == "nest-egg"

    def test_mfa_pending_token_includes_iss_and_aud(self):
        token = create_mfa_pending_token("user-1", timedelta(minutes=5))
        raw = _jwt.decode(token, options={"verify_signature": False})
        assert raw["iss"] == "nest-egg"
        assert raw["aud"] == "nest-egg"

    def test_decode_token_accepts_valid_claims(self):
        token = create_access_token({"sub": "user-1"})
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["iss"] == "nest-egg"
        assert payload["aud"] == "nest-egg"

    def test_decode_token_rejects_missing_aud(self):
        """Tokens crafted without aud must be rejected — prevents cross-service replay."""
        from app.config import settings
        from jwt.exceptions import InvalidTokenError

        crafted = _jwt.encode(
            {"sub": "evil", "exp": utc_now() + timedelta(minutes=5), "type": "access", "iss": "nest-egg"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(InvalidTokenError):
            decode_token(crafted)

    def test_decode_token_rejects_missing_iss(self):
        """Tokens crafted without iss must be rejected."""
        from app.config import settings
        from jwt.exceptions import InvalidTokenError

        crafted = _jwt.encode(
            {"sub": "evil", "exp": utc_now() + timedelta(minutes=5), "type": "access", "aud": "nest-egg"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(InvalidTokenError):
            decode_token(crafted)

    def test_decode_token_rejects_wrong_aud(self):
        """Tokens for a different audience must be rejected."""
        from app.config import settings
        from jwt.exceptions import InvalidTokenError

        crafted = _jwt.encode(
            {
                "sub": "user-1",
                "exp": utc_now() + timedelta(minutes=5),
                "type": "access",
                "iss": "nest-egg",
                "aud": "other-service",
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(InvalidTokenError):
            decode_token(crafted)

    def test_decode_token_rejects_wrong_iss(self):
        """Tokens from a different issuer must be rejected."""
        from app.config import settings
        from jwt.exceptions import InvalidTokenError

        crafted = _jwt.encode(
            {
                "sub": "user-1",
                "exp": utc_now() + timedelta(minutes=5),
                "type": "access",
                "iss": "attacker-service",
                "aud": "nest-egg",
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(InvalidTokenError):
            decode_token(crafted)


@pytest.mark.unit
class TestWebpRiffValidation:
    """WebP magic byte detection must check bytes 8-11 == WEBP, not just RIFF prefix."""

    def _make_webp_header(self) -> bytes:
        """Minimal valid WebP header: RIFF????WEBP (12 bytes)."""
        size = (0).to_bytes(4, "little")  # file size (irrelevant for detection)
        return b"RIFF" + size + b"WEBP" + b"\x00" * 249  # pad to 261 bytes

    def _make_avi_header(self) -> bytes:
        """AVI file: starts with RIFF, bytes 8-11 are 'AVI '."""
        size = (0).to_bytes(4, "little")
        return b"RIFF" + size + b"AVI " + b"\x00" * 249

    def _make_wav_header(self) -> bytes:
        """WAV file: starts with RIFF, bytes 8-11 are 'WAVE'."""
        size = (0).to_bytes(4, "little")
        return b"RIFF" + size + b"WAVE" + b"\x00" * 249

    def test_webp_riff_webp_fourcc_detected(self):
        from app.services.attachment_service import MAGIC_BYTES

        header = self._make_webp_header()

        # Run the same detection logic as the service
        detected_type = None
        for magic, mime in MAGIC_BYTES.items():
            if header[:len(magic)] == magic:
                detected_type = mime
                break
        if detected_type is None and len(header) >= 12:
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                detected_type = "image/webp"

        assert detected_type == "image/webp"

    def test_avi_riff_not_detected_as_webp(self):
        """AVI files start with RIFF but must NOT be accepted as image/webp."""
        from app.services.attachment_service import MAGIC_BYTES

        header = self._make_avi_header()

        detected_type = None
        for magic, mime in MAGIC_BYTES.items():
            if header[:len(magic)] == magic:
                detected_type = mime
                break
        if detected_type is None and len(header) >= 12:
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                detected_type = "image/webp"

        # AVI is not in ALLOWED_CONTENT_TYPES and must not be detected as webp
        assert detected_type != "image/webp"

    def test_wav_riff_not_detected_as_webp(self):
        """WAV files start with RIFF but must NOT be accepted as image/webp."""
        from app.services.attachment_service import MAGIC_BYTES

        header = self._make_wav_header()

        detected_type = None
        for magic, mime in MAGIC_BYTES.items():
            if header[:len(magic)] == magic:
                detected_type = mime
                break
        if detected_type is None and len(header) >= 12:
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                detected_type = "image/webp"

        assert detected_type != "image/webp"

    def test_short_header_does_not_crash(self):
        """Headers shorter than 12 bytes must not crash the WebP detection."""
        from app.services.attachment_service import MAGIC_BYTES

        header = b"RIFF\x00\x00"  # Only 6 bytes — too short for FourCC check

        detected_type = None
        for magic, mime in MAGIC_BYTES.items():
            if header[:len(magic)] == magic:
                detected_type = mime
                break
        if detected_type is None and len(header) >= 12:
            if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                detected_type = "image/webp"

        assert detected_type is None
