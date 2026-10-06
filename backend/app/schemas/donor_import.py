from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import ImportStatus


class ImportRowError(BaseModel):
    row: int
    phone: Optional[str] = None
    errors: List[str]
    raw_data: Optional[Dict[str, Any]] = None


class ImportRowPreview(BaseModel):
    row: int
    full_name: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    normalized_phone: Optional[str] = None
    district: Optional[str] = None
    is_available: Optional[bool] = True
    is_existing: bool = False
    is_valid: bool = True
    errors: List[str] = []


class DonorImportPreviewResponse(BaseModel):
    filename: str
    file_format: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    new_donors: int
    existing_donors: int
    preview_rows: List[ImportRowPreview]
    errors: List[ImportRowError]


class DonorImportBatchResponse(BaseModel):
    id: int
    batch_code: str
    hospital_id: Optional[int] = None
    uploaded_by_user_id: Optional[int] = None
    filename: str
    file_format: str
    total_records: int
    successful_records: int
    failed_records: int
    status: ImportStatus
    error_summary: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DonorImportResponse(BaseModel):
    batch: DonorImportBatchResponse
    total_records: int
    successful_records: int
    failed_records: int
    new_donors_created: int
    existing_donors_updated: int
    errors: List[ImportRowError] = []
