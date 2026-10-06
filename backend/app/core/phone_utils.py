import re
from app.core.exceptions import ValidationException


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to standard E.164 (+91XXXXXXXXXX) format for Indian mobile numbers
    or standard E.164 for international numbers.
    """
    if not phone or not isinstance(phone, (str, int)):
        raise ValidationException("Phone number is required.")

    # Convert int/float to string if coming from excel
    phone_str = str(phone).strip()
    if phone_str.endswith(".0"):
        phone_str = phone_str[:-2]

    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone_str)

    # Handle standard 10-digit Indian numbers starting with 6-9
    if re.match(r"^[6-9]\d{9}$", cleaned):
        return f"+91{cleaned}"

    # Handle 11-digit starting with 0
    if re.match(r"^0[6-9]\d{9}$", cleaned):
        return f"+91{cleaned[1:]}"

    # Handle 12-digit starting with 91
    if re.match(r"^91[6-9]\d{9}$", cleaned):
        return f"+{cleaned}"

    # Handle full E.164 format with +91
    if re.match(r"^\+91[6-9]\d{9}$", cleaned):
        return cleaned

    # Fallback for international numbers: ensure begins with + and has 10-15 digits
    if re.match(r"^\+\d{10,15}$", cleaned):
        return cleaned

    raise ValidationException(
        f"Invalid phone number format: '{phone}'. Expected 10-digit Indian mobile (e.g. 9847012345) or E.164 (+91XXXXXXXXXX)."
    )
