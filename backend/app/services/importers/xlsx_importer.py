import io
from typing import Any, Dict, List
import openpyxl
from app.core.exceptions import ValidationException
from app.services.importers.base_importer import (
    BaseImporter,
    RawImportRow,
    normalize_header,
    parse_boolean_value,
)


class XLSXImporter(BaseImporter):
    def parse(self, content: bytes) -> List[RawImportRow]:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        except Exception as e:
            raise ValidationException(f"Failed to open Excel workbook: {str(e)}")

        sheet = wb.active
        if not sheet:
            raise ValidationException("Excel file contains no active sheets.")

        rows_iter = sheet.iter_rows(values_only=True)
        try:
            raw_headers = next(rows_iter, None)
        except Exception as e:
            raise ValidationException(f"Failed to read header from Excel sheet: {str(e)}")

        if not raw_headers or not any(h is not None for h in raw_headers):
            raise ValidationException("Excel sheet is empty or has no header row.")

        header_mapping: Dict[int, str] = {}
        for idx, header in enumerate(raw_headers):
            if header is not None:
                canonical = normalize_header(str(header))
                if canonical:
                    header_mapping[idx] = canonical

        # Verify minimum essential headers exist
        mapped_columns = set(header_mapping.values())
        if not ("full_name" in mapped_columns and "phone" in mapped_columns and "blood_group" in mapped_columns):
            raise ValidationException(
                f"Missing required columns in Excel sheet header. Found: {list(mapped_columns)}. "
                "Required at minimum: 'full_name', 'blood_group', 'phone'."
            )

        rows: List[RawImportRow] = []
        for row_num, row_values in enumerate(rows_iter, start=2):
            if not row_values or not any(cell is not None and str(cell).strip() != "" for cell in row_values):
                # Skip empty rows
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

            for idx, cell_val in enumerate(row_values):
                if cell_val is None:
                    continue

                col_name = header_mapping.get(idx)
                if not col_name:
                    continue

                # Format cell value cleanly
                if isinstance(cell_val, (int, float)):
                    # Handle integer phones stored as float/int in excel
                    if isinstance(cell_val, float) and cell_val.is_integer():
                        val_str = str(int(cell_val))
                    else:
                        val_str = str(cell_val)
                elif isinstance(cell_val, bool):
                    val_str = "true" if cell_val else "false"
                else:
                    val_str = str(cell_val).strip()

                raw_dict[col_name] = val_str
                if col_name in row_data:
                    if col_name == "is_available":
                        row_data["is_available"] = parse_boolean_value(cell_val)
                    else:
                        row_data[col_name] = val_str if val_str != "" else None

            rows.append(
                RawImportRow(
                    row_number=row_num,
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

        wb.close()
        return rows
