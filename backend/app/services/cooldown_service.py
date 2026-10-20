from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
from app.core.config import settings


@dataclass
class CooldownEligibility:
    is_eligible: bool
    last_donation_date: Optional[date]
    eligible_from: Optional[date]
    days_remaining: int
    days_since_last_donation: Optional[int]
    cooldown_days_required: int


def get_required_cooldown_days(donation_type: str = "Whole Blood") -> int:
    """
    Returns the configured project policy cooldown period in days based on donation type.
    Note: These cooldown intervals (Whole Blood: 90d, Platelets: 14d, Plasma: 28d) reflect
    configurable Rakthasethu project operational policies (derived from Drugs & Cosmetics Rules)
    rather than immutable medical absolutes.
    """
    type_normalized = (donation_type or "Whole Blood").strip().lower()
    if "platelet" in type_normalized:
        return settings.PLATELET_COOLDOWN_DAYS
    elif "plasma" in type_normalized:
        return settings.PLASMA_COOLDOWN_DAYS
    else:
        # Default Whole Blood
        return settings.WHOLE_BLOOD_COOLDOWN_DAYS


def calculate_cooldown_eligibility(
    last_donation_date: Optional[date],
    donation_type: str = "Whole Blood",
    reference_date: Optional[date] = None,
) -> CooldownEligibility:
    """
    Calculates cooldown eligibility against the configured project cooldown policy.
    - If never donated (last_donation_date is None): 100% eligible, days_remaining = 0.
    - If last_donation_date + cooldown <= reference_date: eligible.
    - Otherwise: ineligible until eligible_from date.
    """
    if reference_date is None:
        reference_date = date.today()

    required_days = get_required_cooldown_days(donation_type)

    if last_donation_date is None:
        return CooldownEligibility(
            is_eligible=True,
            last_donation_date=None,
            eligible_from=None,
            days_remaining=0,
            days_since_last_donation=None,
            cooldown_days_required=required_days,
        )

    eligible_from = last_donation_date + timedelta(days=required_days)
    days_since = (reference_date - last_donation_date).days
    days_left = (eligible_from - reference_date).days

    if days_left <= 0:
        return CooldownEligibility(
            is_eligible=True,
            last_donation_date=last_donation_date,
            eligible_from=eligible_from,
            days_remaining=0,
            days_since_last_donation=max(0, days_since),
            cooldown_days_required=required_days,
        )
    else:
        return CooldownEligibility(
            is_eligible=False,
            last_donation_date=last_donation_date,
            eligible_from=eligible_from,
            days_remaining=days_left,
            days_since_last_donation=max(0, days_since),
            cooldown_days_required=required_days,
        )
