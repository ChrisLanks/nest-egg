"""Password validation service with strength checking and breach detection."""

import hashlib
import logging
import re
from typing import List, Tuple, Optional

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class PasswordValidationService:
    """Service for validating password strength and security."""

    # Common passwords to block (top 100 most common)
    # In production, this should be a much larger list or use Have I Been Pwned API
    COMMON_PASSWORDS = {
        "password",
        "123456",
        "123456789",
        "12345678",
        "12345",
        "1234567",
        "password1",
        "12345678910",
        "qwerty",
        "abc123",
        "111111",
        "123123",
        "password123",
        "1234567890",
        "000000",
        "qwerty123",
        "1q2w3e4r",
        "admin",
        "letmein",
        "welcome",
        "monkey",
        "dragon",
        "master",
        "sunshine",
        "princess",
        "football",
        "shadow",
        "michael",
        "jennifer",
        "computer",
        "bailey",
        "harley",
        "whatever",
        "arsenal",
        "thomas",
        "trustno1",
        "jordan",
        "password1234",
        "passw0rd",
        "superman",
        "batman",
        "test123",
        "testing",
        "sample",
        "default",
        "admin123",
    }

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength against security requirements.

        Requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        - Not a common password

        Args:
            password: The password to validate

        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []

        # Check minimum length
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")

        # Check for uppercase letter
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        # Check for lowercase letter
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        # Check for digit
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/`~]', password):
            errors.append("Password must contain at least one special character (!@#$%^&* etc.)")

        # Check against common passwords
        if password.lower() in PasswordValidationService.COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a more unique password")

        # Check for sequential characters (e.g., "12345", "abcde")
        if re.search(
            r"(?:0123|1234|2345|3456|4567|5678|6789|7890|abcd|bcde|cdef|defg|efgh|fghi|ghij)",
            password.lower(),
        ):
            errors.append("Password contains sequential characters")

        # Check for repeated characters (e.g., "aaaaaa", "111111")
        if re.search(r"(.)\1{5,}", password):
            errors.append("Password contains too many repeated characters")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    async def check_password_breach(password: str) -> Tuple[bool, Optional[int]]:
        """
        Check if password has been exposed in known data breaches using Have I Been Pwned API.

        Uses k-anonymity model: only sends first 5 characters of SHA-1 hash to the API,
        ensuring the actual password never leaves our server.

        Args:
            password: The password to check

        Returns:
            Tuple of (is_breached: bool, breach_count: Optional[int])
            - is_breached: True if password found in breach database
            - breach_count: Number of times seen in breaches (None if not breached)
        """
        try:
            # Hash password with SHA-1 (required by HIBP k-anonymity API — not used for security)
            sha1_hash = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()  # nosec B324

            # Split hash: first 5 chars sent to API, rest checked locally
            hash_prefix = sha1_hash[:5]
            hash_suffix = sha1_hash[5:]

            # Call HIBP API with k-anonymity (only send first 5 chars)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://api.pwnedpasswords.com/range/{hash_prefix}",
                    headers={"User-Agent": "NestEgg-PasswordChecker"},
                )

            if response.status_code != 200:
                # If API fails, log but don't block registration
                # Better to allow signup than block legitimate users
                logger.warning("HIBP API error: status=%s", response.status_code)
                return False, None

            # Parse response: each line is "SUFFIX:COUNT"
            hashes = response.text.splitlines()
            for hash_line in hashes:
                parts = hash_line.split(":")
                if len(parts) == 2:
                    returned_suffix, count = parts
                    if returned_suffix == hash_suffix:
                        # Password found in breach database
                        return True, int(count)

            # Password not found in breaches
            return False, None

        except httpx.TimeoutException:
            # Timeout - don't block user registration
            logger.warning("HIBP API timeout - skipping breach check")
            return False, None
        except Exception as e:
            # Any other error - fail open (allow registration)
            logger.warning("HIBP API error: %s", e)
            return False, None

    @staticmethod
    async def validate_and_raise_async(password: str, check_breach: bool = True) -> None:
        """
        Validate password and raise HTTPException if invalid.
        Async version that includes breach checking.

        Args:
            password: The password to validate
            check_breach: Whether to check against breach database (default True)

        Raises:
            HTTPException: If password doesn't meet requirements or is breached
        """
        # First check strength requirements
        is_valid, errors = PasswordValidationService.validate_password_strength(password)

        # Then check if password has been breached (if enabled)
        is_breached = False
        breach_count = None
        if check_breach:
            is_breached, breach_count = await PasswordValidationService.check_password_breach(
                password
            )
            if is_breached:
                errors.append(
                    f"This password has been exposed in data breaches "
                    f"({breach_count:,} times). Please choose a different password"
                )

        if not is_valid or is_breached:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "errors": errors,
                },
            )

    @staticmethod
    def validate_and_raise(password: str) -> None:
        """
        Validate password and raise HTTPException if invalid.

        Args:
            password: The password to validate

        Raises:
            HTTPException: If password doesn't meet requirements
        """
        is_valid, errors = PasswordValidationService.validate_password_strength(password)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "errors": errors,
                },
            )


# Create singleton instance
password_validation_service = PasswordValidationService()
