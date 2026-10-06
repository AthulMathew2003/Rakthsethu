import os
from app.core.exceptions import ValidationException
from app.services.importers.base_importer import BaseImporter, RawImportRow
from app.services.importers.csv_importer import CSVImporter
from app.services.importers.xlsx_importer import XLSXImporter


def get_importer(filename: str) -> BaseImporter:
    """Factory to return appropriate file parser based on filename extension."""
    if not filename:
        raise ValidationException("Filename is required.")

    _, ext = os.path.splitext(filename.lower())
    if ext == ".csv":
        return CSVImporter()
    elif ext in (".xlsx", ".xlsm"):
        return XLSXImporter()
    elif ext == ".xls":
        raise ValidationException(
            "Legacy .xls format is not supported. Please convert and save your spreadsheet as .xlsx or .csv."
        )
    else:
        raise ValidationException(
            f"Unsupported file format '{ext}'. Allowed formats are .csv and .xlsx."
        )


__all__ = ["BaseImporter", "RawImportRow", "CSVImporter", "XLSXImporter", "get_importer"]
