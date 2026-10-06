import csv
import io
from typing import Any, Dict, List
from app.core.exceptions import ValidationException
from app.services.importers.base_importer import (
    BaseImporter,
    RawImportRow,
    normalize_header,
    parse_boolean_value,
)


class CSVImporter(BaseImporter):
    def parse(self, content: bytes) -> List[RawImportRow]:
        # Handle encoding: try utf-8-sig (handles BOM), then utf-8, then latin-1
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            raise ValidationException("Unable to decode CSV file. Please ensure it is saved in UTF-8 format.")

        stream = io.StringIO(text.strip())
        reader = csv.reader(stream)

        try:
            raw_headers = next(reader, None)
        except Exception as e:
            raise ValidationException(f"Failed to read CSV header: {str(e)}")

        if not raw_headers:
            raise ValidationException("CSV file is empty or has no header row.")

        # Map header index to canonical column name
        header_mapping: Dict[int, str] = {}
        for idx, header in enumerate(raw_headers):
            canonical = normalize_header(header)
            if canonical:
                header_mapping[idx] = canonical

        # Verify minimum essential headers exist
        mapped_columns = set(header_mapping.values())
        if not ("full_name" in mapped_columns and "phone" in mapped_columns and "blood_group" in mapped_columns):
            raise ValidationException(
                f"Missing required columns in CSV header. Found: {list(mapped_columns)}. "
                "Required at minimum: 'full_name', 'blood_group', 'phone'."
            )

        rows: List[RawImportRow] = []
        for line_num, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                # Skip empty lines
                continue

            raw_dict: Dict[str, Any] = {}
            row_data: Dict[str, Any] = {
                "full_name": None,
                "blood_group": None,
                "phone": None,
                "email": None,
                "gender": None,
                "district": None,
                "panchayat": None,
                "address": None,
                "is_available": None,
            }

            for idx, val in enumerate(row):
                val_str = val.strip() if isinstance(val, str) else str(val).strip()
                col_name = header_mapping.get(idx)
                if col_name:
                    raw_dict[col_name] = val_str
                    if col_name in row_data:
                        if col_name == "is_available":
                            row_data["is_available"] = parse_boolean_value(val_str) if val_str != "" else None
                        else:
                            row_data[col_name] = val_str if val_str != "" else None

            rows.append(
                RawImportRow(
                    row_number=line_num,
                    full_name=row_data["full_name"],
                    blood_group=row_data["blood_group"],
                    phone=row_data["phone"],
                    email=row_data["email"],
                    gender=row_data["gender"],
                    district=row_data["district"],
                    panchayat=row_data["panchayat"],
                    address=row_data["address"],
                    is_available=row_data["is_available"],
                    raw_data=raw_dict,
                )
            )

        return rows
