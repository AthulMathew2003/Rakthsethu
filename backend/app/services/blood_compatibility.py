from typing import Dict, List, Set
from app.models.enums import BloodGroup

# Red Blood Cell / Whole Blood ABO & Rh D-antigen compatibility matrix.
# Key = Recipient (Patient) Blood Group
# Value = List of Compatible Donor Blood Groups in preference order (identical group first, universal fallback next)
RECIPIENT_TO_COMPATIBLE_DONORS: Dict[BloodGroup, List[BloodGroup]] = {
    # O Negative: Universal RBC donor, can only receive O-
    BloodGroup.O_NEGATIVE: [
        BloodGroup.O_NEGATIVE,
    ],
    # O Positive: Can receive O+ and O-
    BloodGroup.O_POSITIVE: [
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    ],
    # A Negative: Can receive A- and O-
    BloodGroup.A_NEGATIVE: [
        BloodGroup.A_NEGATIVE,
        BloodGroup.O_NEGATIVE,
    ],
    # A Positive: Can receive A+, A-, O+, O-
    BloodGroup.A_POSITIVE: [
        BloodGroup.A_POSITIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    ],
    # B Negative: Can receive B- and O-
    BloodGroup.B_NEGATIVE: [
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_NEGATIVE,
    ],
    # B Positive: Can receive B+, B-, O+, O-
    BloodGroup.B_POSITIVE: [
        BloodGroup.B_POSITIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    ],
    # AB Negative: Can receive AB-, A-, B-, O-
    BloodGroup.AB_NEGATIVE: [
        BloodGroup.AB_NEGATIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_NEGATIVE,
    ],
    # AB Positive: Universal RBC recipient, can receive from all groups
    BloodGroup.AB_POSITIVE: [
        BloodGroup.AB_POSITIVE,
        BloodGroup.AB_NEGATIVE,
        BloodGroup.A_POSITIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.B_POSITIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    ],
}


def get_compatible_donor_groups(recipient_group: BloodGroup) -> List[BloodGroup]:
    """
    Returns the ordered list of donor blood groups compatible with the given recipient.
    Identical blood type is prioritized first, followed by compatible subtypes and universal donors.
    """
    return RECIPIENT_TO_COMPATIBLE_DONORS.get(recipient_group, [recipient_group])


def is_blood_compatible(donor_group: BloodGroup, recipient_group: BloodGroup) -> bool:
    """
    Validates if a donor's blood group is biologically compatible for a recipient.
    """
    compatible_groups = RECIPIENT_TO_COMPATIBLE_DONORS.get(recipient_group, [])
    return donor_group in compatible_groups
