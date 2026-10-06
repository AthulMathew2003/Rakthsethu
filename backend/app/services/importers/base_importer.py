import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RawImportRow:
    row_number: int
    full_name: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    district: Optional[str] = None
    panchayat: Optional[str] = None
    address: Optional[str] = None
    is_available: Optional[bool] = None
    raw_data: Optional[Dict[str, Any]] = None


# Canonical header map mapping normalized column keys to RawImportRow attribute names
HEADER_ALIASES: Dict[str, str] = {
    # Full Name
    "fullname": "full_name",
    "full_name": "full_name",
    "name": "full_name",
    "donorname": "full_name",
    "donor_name": "full_name",
    "patientname": "full_name",
    # Blood Group
    "bloodgroup": "blood_group",
    "blood_group": "blood_group",
    "blood": "blood_group",
    "group": "blood_group",
    "bg": "blood_group",
    # Phone / Mobile
    "phone": "phone",
    "phonenumber": "phone",
    "phone_number": "phone",
    "mobile": "phone",
    "mobilenumber": "phone",
    "mobile_number": "phone",
    "contact": "phone",
    "contactnumber": "phone",
    "contact_phone": "phone",
    # Email
    "email": "email",
    "emailid": "email",
    "email_id": "email",
    "emailaddress": "email",
    "email_address": "email",
    "mail": "email",
    # Gender
    "gender": "gender",
    "sex": "gender",
    # District
    "district": "district",
    "city": "district",
    # Panchayat / Municipality
    "panchayat": "panchayat",
    "municipality": "panchayat",
    "localbody": "panchayat",
    "local_body": "panchayat",
    "taluk": "panchayat",
    # Address
    "address": "address",
    "residentialaddress": "address",
    "residential_address": "address",
    # Availability
    "isavailable": "is_available",
    "is_available": "is_available",
    "available": "is_available",
    "availability": "is_available",
    "status": "is_available",
}


def normalize_header(header: str) -> Optional[str]:
    """Cleans up header name (strips whitespace, symbols) and matches to canonical attribute."""
    if not header or not isinstance(header, str):
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", header.strip().lower().replace(" ", "_"))
    return HEADER_ALIASES.get(cleaned, cleaned)


def parse_boolean_value(val: Any) -> Optional[bool]:
    """Parse string/numeric value into a boolean."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(int(val))
    str_val = str(val).strip().lower()
    if str_val in ("true", "1", "yes", "y", "active", "available", "t"):
        return True
    if str_val in ("false", "0", "no", "n", "inactive", "unavailable", "f"):
        return False
    return None


class BaseImporter(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> List[RawImportRow]:
        """Parses raw binary content into a list of RawImportRow objects."""
        pass
