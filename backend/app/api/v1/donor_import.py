import math
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import HospitalAccessDeniedException, ResourceNotFoundException
from app.core.response import ApiResponse, success_response
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.donor_import_batch_repository import DonorImportBatchRepository
from app.schemas.common import PaginatedData
from app.schemas.donor_import import (
    DonorImportBatchResponse,
    DonorImportPreviewResponse,
    DonorImportResponse,
)
from app.services.donor_import_service import DonorImportService

router = APIRouter(prefix="/donors", tags=["Donor Bulk Import"])


@router.post(
    "/import/preview",
    response_model=ApiResponse[DonorImportPreviewResponse],
    summary="Preview and validate a donor CSV/XLSX file without modifying the database",
)
async def preview_donor_import(
    file: UploadFile = File(..., description="CSV or XLSX donor dataset"),
    hospital_id: Optional[int] = Form(None, description="Target hospital ID (optional for Super Admin)"),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    content = await file.read()
    service = DonorImportService(session)
    preview = await service.preview_import(
        filename=file.filename or "upload.csv",
        file_bytes=content,
        requested_hospital_id=hospital_id,
        current_user=current_user,
    )
    return success_response(data=preview, message="Donor import file preview generated successfully.")


@router.post(
    "/import",
    response_model=ApiResponse[DonorImportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Execute bulk donor import from CSV/XLSX file into the canonical registry",
)
async def execute_donor_import(
    file: UploadFile = File(..., description="CSV or XLSX donor dataset"),
    hospital_id: Optional[int] = Form(None, description="Target hospital ID (optional for Super Admin)"),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    content = await file.read()
    service = DonorImportService(session)
    result = await service.execute_import(
        filename=file.filename or "upload.csv",
        file_bytes=content,
        requested_hospital_id=hospital_id,
        current_user=current_user,
    )
    return success_response(data=result, message="Donor dataset imported successfully.")


@router.get(
    "/imports",
    response_model=ApiResponse[PaginatedData[DonorImportBatchResponse]],
    summary="List donor bulk import batch history (Paginated)",
)
async def list_import_batches(
    hospital_id: Optional[int] = Query(None, description="Filter batches by hospital ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    # RBAC hospital scoping
    if current_user.role != UserRole.SUPER_ADMIN:
        if not current_user.hospital_id:
            raise HospitalAccessDeniedException("User is not associated with any hospital.")
        if hospital_id and hospital_id != current_user.hospital_id:
            raise HospitalAccessDeniedException("Access denied to another hospital's import history.")
        hospital_id = current_user.hospital_id

    batch_repo = DonorImportBatchRepository(session)
    items, total = await batch_repo.list_batches(hospital_id=hospital_id, page=page, page_size=page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return success_response(
        data=PaginatedData(
            items=[DonorImportBatchResponse.model_validate(b) for b in items],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
        message="Import batches retrieved successfully.",
    )


@router.get(
    "/imports/{batch_id}",
    response_model=ApiResponse[DonorImportBatchResponse],
    summary="Retrieve details and status for a specific donor import batch",
)
async def get_import_batch(
    batch_id: int,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.STAFF)),
    session: AsyncSession = Depends(get_db),
):
    batch_repo = DonorImportBatchRepository(session)
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise ResourceNotFoundException("DonorImportBatch", batch_id)

    # Scoping check
    if current_user.role != UserRole.SUPER_ADMIN:
        if batch.hospital_id != current_user.hospital_id:
            raise HospitalAccessDeniedException("Access denied to another hospital's import batch.")

    return success_response(
        data=DonorImportBatchResponse.model_validate(batch),
        message="Import batch retrieved successfully.",
    )
