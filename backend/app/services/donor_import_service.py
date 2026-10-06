from datetime import datetime, timezone
import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import (
    HospitalAccessDeniedException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.phone_utils import normalize_phone_number
from app.models.donor import Donor
from app.models.donor_import_batch import DonorImportBatch
from app.models.enums import BloodGroup, ImportStatus, UserRole
from app.models.user import User
from app.repositories.donor_import_batch_repository import DonorImportBatchRepository
from app.repositories.donor_repository import DonorRepository
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.donor_import import (
    DonorImportBatchResponse,
    DonorImportPreviewResponse,
    DonorImportResponse,
    ImportRowError,
    ImportRowPreview,
)
from app.services.importers import RawImportRow, get_importer

# Valid blood group mapping
BLOOD_GROUP_MAP: Dict[str, BloodGroup] = {
    "A+": BloodGroup.A_POSITIVE,
    "A-": BloodGroup.A_NEGATIVE,
    "B+": BloodGroup.B_POSITIVE,
    "B-": BloodGroup.B_NEGATIVE,
    "AB+": BloodGroup.AB_POSITIVE,
    "AB-": BloodGroup.AB_NEGATIVE,
    "O+": BloodGroup.O_POSITIVE,
    "O-": BloodGroup.O_NEGATIVE,
    # Common text variations
    "A POSITIVE": BloodGroup.A_POSITIVE,
    "A NEGATIVE": BloodGroup.A_NEGATIVE,
    "B POSITIVE": BloodGroup.B_POSITIVE,
    "B NEGATIVE": BloodGroup.B_NEGATIVE,
    "AB POSITIVE": BloodGroup.AB_POSITIVE,
    "AB NEGATIVE": BloodGroup.AB_NEGATIVE,
    "O POSITIVE": BloodGroup.O_POSITIVE,
    "O NEGATIVE": BloodGroup.O_NEGATIVE,
}

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class DonorImportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.donor_repo = DonorRepository(session)
        self.batch_repo = DonorImportBatchRepository(session)
        self.hospital_repo = HospitalRepository(session)

    def resolve_target_hospital_id(
        self, requested_hospital_id: Optional[int], current_user: User
    ) -> Optional[int]:
        """Validates and resolves target hospital ID based on RBAC rules."""
        if current_user.role == UserRole.SUPER_ADMIN:
            return requested_hospital_id
        elif current_user.role in (UserRole.HOSPITAL_ADMIN, UserRole.STAFF):
            if not current_user.hospital_id:
                raise HospitalAccessDeniedException("User is not associated with any hospital.")
            if requested_hospital_id and requested_hospital_id != current_user.hospital_id:
                raise HospitalAccessDeniedException("You cannot import donors for another hospital.")
            return current_user.hospital_id
        else:
            raise HospitalAccessDeniedException("Unauthorized role for donor import.")

    def validate_file_metadata(self, filename: str, file_bytes: bytes) -> str:
        """Validates file size and format."""
        max_bytes = settings.MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValidationException(
                f"File size ({len(file_bytes) / (1024 * 1024):.1f}MB) exceeds maximum allowed limit of {settings.MAX_IMPORT_FILE_SIZE_MB}MB."
            )

        _, ext = os.path.splitext(filename.lower())
        if ext not in (".csv", ".xlsx", ".xlsm"):
            raise ValidationException(
                f"Unsupported file format '{ext}'. Allowed formats are .csv and .xlsx."
            )
        return "csv" if ext == ".csv" else "xlsx"

    def validate_row(self, row: RawImportRow) -> Tuple[Optional[BloodGroup], Optional[str], List[str]]:
        """
        Validates row fields according to canonical donor rules.
        Returns (validated_blood_group, normalized_phone, error_list).
        """
        errors: List[str] = []

        # 1. Full name validation
        if not row.full_name or not row.full_name.strip():
            errors.append("Full name is required.")
        elif len(row.full_name.strip()) > 150:
            errors.append("Full name cannot exceed 150 characters.")

        # 2. Blood group validation
        blood_group_enum: Optional[BloodGroup] = None
        if not row.blood_group or not row.blood_group.strip():
            errors.append("Blood group is required.")
        else:
            bg_clean = row.blood_group.strip().upper()
            if bg_clean in BLOOD_GROUP_MAP:
                blood_group_enum = BLOOD_GROUP_MAP[bg_clean]
            else:
                errors.append(f"Invalid blood group '{row.blood_group}'. Must be one of A+, A-, B+, B-, AB+, AB-, O+, O-.")

        # 3. Phone normalization and validation
        normalized_phone: Optional[str] = None
        if not row.phone or not str(row.phone).strip():
            errors.append("Phone number is required.")
        else:
            try:
                normalized_phone = normalize_phone_number(row.phone)
            except ValidationException as e:
                errors.append(str(e))

        # 4. District validation
        if not row.district or not row.district.strip():
            errors.append("District is required.")
        elif len(row.district.strip()) > 100:
            errors.append("District cannot exceed 100 characters.")

        # 5. Email validation (optional)
        if row.email and row.email.strip():
            email_clean = row.email.strip().lower()
            if len(email_clean) > 120 or not EMAIL_REGEX.match(email_clean):
                errors.append(f"Invalid email address format: '{row.email}'.")

        # 6. Optional field length checks
        if row.gender and len(row.gender.strip()) > 20:
            errors.append("Gender cannot exceed 20 characters.")
        if row.panchayat and len(row.panchayat.strip()) > 100:
            errors.append("Panchayat cannot exceed 100 characters.")

        return blood_group_enum, normalized_phone, errors

    async def preview_import(
        self,
        filename: str,
        file_bytes: bytes,
        requested_hospital_id: Optional[int],
        current_user: User,
    ) -> DonorImportPreviewResponse:
        """
        Parses and validates the import file, checks for existing donors,
        and returns a detailed preview without writing to the database.
        """
        file_format = self.validate_file_metadata(filename, file_bytes)
        target_hospital_id = self.resolve_target_hospital_id(requested_hospital_id, current_user)

        if target_hospital_id:
            hosp = await self.hospital_repo.get_by_id(target_hospital_id)
            if not hosp:
                raise ResourceNotFoundException("Hospital", target_hospital_id)

        importer = get_importer(filename)
        raw_rows = importer.parse(file_bytes)

        if not raw_rows:
            raise ValidationException("File contains no data rows.")

        if len(raw_rows) > settings.MAX_IMPORT_ROWS:
            raise ValidationException(
                f"File contains {len(raw_rows)} rows, exceeding maximum limit of {settings.MAX_IMPORT_ROWS} rows."
            )

        valid_count = 0
        invalid_count = 0
        new_donors_count = 0
        existing_donors_count = 0

        preview_rows: List[ImportRowPreview] = []
        errors_list: List[ImportRowError] = []
        seen_phones_in_batch: Set[str] = set()

        for row in raw_rows:
            bg_enum, norm_phone, errors = self.validate_row(row)

            is_existing = False
            is_valid = len(errors) == 0

            if is_valid and norm_phone:
                # Check for intra-batch duplicate
                if norm_phone in seen_phones_in_batch:
                    is_existing = True
                    existing_donors_count += 1
                else:
                    seen_phones_in_batch.add(norm_phone)
                    # Check database for existing donor
                    existing_db_donor = await self.donor_repo.get_by_phone(norm_phone)
                    if existing_db_donor:
                        is_existing = True
                        existing_donors_count += 1
                    else:
                        new_donors_count += 1
                valid_count += 1
            else:
                invalid_count += 1
                errors_list.append(
                    ImportRowError(
                        row=row.row_number,
                        phone=str(row.phone) if row.phone else None,
                        errors=errors,
                        raw_data=row.raw_data,
                    )
                )

            # Collect preview (limit to first 50 rows to keep response fast)
            if len(preview_rows) < 50:
                preview_rows.append(
                    ImportRowPreview(
                        row=row.row_number,
                        full_name=row.full_name,
                        blood_group=bg_enum.value if bg_enum else row.blood_group,
                        phone=row.phone,
                        normalized_phone=norm_phone,
                        district=row.district,
                        is_available=row.is_available if row.is_available is not None else True,
                        is_existing=is_existing,
                        is_valid=is_valid,
                        errors=errors,
                    )
                )

        return DonorImportPreviewResponse(
            filename=filename,
            file_format=file_format,
            total_rows=len(raw_rows),
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            new_donors=new_donors_count,
            existing_donors=existing_donors_count,
            preview_rows=preview_rows,
            errors=errors_list,
        )

    async def execute_import(
        self,
        filename: str,
        file_bytes: bytes,
        requested_hospital_id: Optional[int],
        current_user: User,
    ) -> DonorImportResponse:
        """
        Processes and imports donor records in an atomic transactional manner,
        creating an audit batch and updating/creating donors.
        """
        file_format = self.validate_file_metadata(filename, file_bytes)
        target_hospital_id = self.resolve_target_hospital_id(requested_hospital_id, current_user)

        if target_hospital_id:
            hosp = await self.hospital_repo.get_by_id(target_hospital_id)
            if not hosp:
                raise ResourceNotFoundException("Hospital", target_hospital_id)

        importer = get_importer(filename)
        raw_rows = importer.parse(file_bytes)

        if not raw_rows:
            raise ValidationException("File contains no data rows.")

        if len(raw_rows) > settings.MAX_IMPORT_ROWS:
            raise ValidationException(
                f"File contains {len(raw_rows)} rows, exceeding maximum limit of {settings.MAX_IMPORT_ROWS} rows."
            )

        # 1. Create import batch record
        batch_code = await self.batch_repo.generate_next_batch_code()
        batch = DonorImportBatch(
            batch_code=batch_code,
            hospital_id=target_hospital_id,
            uploaded_by_user_id=current_user.id,
            filename=filename,
            file_format=file_format,
            total_records=len(raw_rows),
            successful_records=0,
            failed_records=0,
            status=ImportStatus.PROCESSING,
        )
        await self.batch_repo.add(batch)
        await self.session.commit()
        await self.session.refresh(batch)

        successful_count = 0
        failed_count = 0
        new_donors_created = 0
        existing_donors_updated = 0
        row_errors: List[ImportRowError] = []

        try:
            for row in raw_rows:
                bg_enum, norm_phone, errors = self.validate_row(row)

                if errors or not norm_phone or not bg_enum:
                    failed_count += 1
                    row_errors.append(
                        ImportRowError(
                            row=row.row_number,
                            phone=str(row.phone) if row.phone else None,
                            errors=errors,
                            raw_data=row.raw_data,
                        )
                    )
                    continue

                # Check if donor exists
                existing_donor = await self.donor_repo.get_by_phone(norm_phone)
                if existing_donor:
                    # Update existing donor without overwriting fields with None/blank
                    if row.full_name and row.full_name.strip():
                        existing_donor.full_name = row.full_name.strip()
                    if row.district and row.district.strip():
                        existing_donor.district = row.district.strip()
                    if row.email and row.email.strip():
                        existing_donor.email = row.email.strip().lower()
                    if row.gender and row.gender.strip():
                        existing_donor.gender = row.gender.strip()
                    if row.panchayat and row.panchayat.strip():
                        existing_donor.panchayat = row.panchayat.strip()
                    if row.address and row.address.strip():
                        existing_donor.address = row.address.strip()
                    if row.is_available is not None:
                        existing_donor.is_available = row.is_available
                    if not existing_donor.hospital_id and target_hospital_id:
                        existing_donor.hospital_id = target_hospital_id

                    existing_donors_updated += 1
                    successful_count += 1
                else:
                    # Create new canonical donor
                    donor_code = await self.donor_repo.generate_next_donor_code()
                    new_donor = Donor(
                        donor_code=donor_code,
                        hospital_id=target_hospital_id,
                        full_name=row.full_name.strip() if row.full_name else "",
                        blood_group=bg_enum,
                        phone=norm_phone,
                        email=row.email.strip().lower() if row.email and row.email.strip() else None,
                        gender=row.gender.strip() if row.gender and row.gender.strip() else None,
                        district=row.district.strip() if row.district else "",
                        panchayat=row.panchayat.strip() if row.panchayat and row.panchayat.strip() else None,
                        address=row.address.strip() if row.address and row.address.strip() else None,
                        is_active=True,
                        is_available=row.is_available if row.is_available is not None else True,
                    )
                    await self.donor_repo.add(new_donor)
                    new_donors_created += 1
                    successful_count += 1

            # Update batch metadata
            batch.successful_records = successful_count
            batch.failed_records = failed_count
            batch.status = ImportStatus.COMPLETED if successful_count > 0 or failed_count == 0 else ImportStatus.FAILED
            batch.completed_at = datetime.now(timezone.utc)

            if row_errors:
                summary_sample = [f"Row {err.row}: {', '.join(err.errors)}" for err in row_errors[:10]]
                if len(row_errors) > 10:
                    summary_sample.append(f"...and {len(row_errors) - 10} more rows with errors.")
                batch.error_summary = "\n".join(summary_sample)

            await self.session.commit()
            await self.session.refresh(batch)

        except Exception as e:
            await self.session.rollback()
            # Set batch to failed in a separate transaction
            try:
                batch.status = ImportStatus.FAILED
                batch.error_summary = f"Fatal import failure: {str(e)}"
                batch.completed_at = datetime.now(timezone.utc)
                await self.session.commit()
            except Exception:
                pass
            raise ValidationException(f"Failed to complete donor import: {str(e)}")

        return DonorImportResponse(
            batch=DonorImportBatchResponse.model_validate(batch),
            total_records=len(raw_rows),
            successful_records=successful_count,
            failed_records=failed_count,
            new_donors_created=new_donors_created,
            existing_donors_updated=existing_donors_updated,
            errors=row_errors,
        )
