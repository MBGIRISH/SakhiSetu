"""
Eligibility matching engine for government schemes.
"""

import logging
from typing import Any

from app.models import Scheme
from app.schemas import EligibilityResult, UserProfile

logger = logging.getLogger(__name__)


def check_eligibility(user_profile: UserProfile, scheme: Scheme) -> dict[str, Any]:
    """
    Check if a user is eligible for a given scheme.

    Rules:
    - Income <= scheme income_limit (if both specified)
    - State matches (if scheme is state-specific)
    - Age >= min_age and <= max_age (if specified)

    Returns:
        {"eligible": bool, "reason": str}
    """
    reasons_eligible: list[str] = []
    reasons_ineligible: list[str] = []

    # Income check
    if scheme.income_limit is not None and user_profile.income is not None:
        if user_profile.income <= scheme.income_limit:
            reasons_eligible.append(
                f"Income ₹{user_profile.income:,.0f} is within limit of ₹{scheme.income_limit:,.0f}"
            )
        else:
            reasons_ineligible.append(
                f"Income ₹{user_profile.income:,.0f} exceeds limit of ₹{scheme.income_limit:,.0f}"
            )
    elif scheme.income_limit is not None and user_profile.income is None:
        reasons_ineligible.append(
            "Income limit specified for scheme but your income was not provided"
        )
    elif scheme.income_limit is None:
        reasons_eligible.append("No income limit for this scheme")

    # State check (scheme.state = None means All India)
    if scheme.state and scheme.state.strip():
        scheme_states = [s.strip() for s in scheme.state.split(",")]
        if user_profile.state:
            user_state = user_profile.state.strip()
            if any(
                user_state.lower() == s.lower() for s in scheme_states
            ):
                reasons_eligible.append(f"State '{user_state}' is eligible")
            else:
                reasons_ineligible.append(
                    f"Scheme is for {scheme.state}; you are from {user_state}"
                )
        else:
            reasons_ineligible.append(
                "Scheme is state-specific but your state was not provided"
            )
    else:
        reasons_eligible.append("Scheme is available across India")

    # Age check
    if user_profile.age is not None:
        if scheme.min_age is not None and user_profile.age < scheme.min_age:
            reasons_ineligible.append(
                f"Age {user_profile.age} is below minimum {scheme.min_age} years"
            )
        elif scheme.max_age is not None and user_profile.age > scheme.max_age:
            reasons_ineligible.append(
                f"Age {user_profile.age} exceeds maximum {scheme.max_age} years"
            )
        elif scheme.min_age is not None or scheme.max_age is not None:
            reasons_eligible.append("Age criteria satisfied")
    elif scheme.min_age is not None or scheme.max_age is not None:
        reasons_ineligible.append(
            "Scheme has age criteria but your age was not provided"
        )

    # Determine final eligibility
    eligible = len(reasons_ineligible) == 0
    if eligible:
        reason = "Eligible. " + "; ".join(reasons_eligible)
    else:
        reason = "Not eligible. " + "; ".join(reasons_ineligible)

    return {"eligible": eligible, "reason": reason}


def check_eligibility_result(
    user_profile: UserProfile, scheme: Scheme
) -> EligibilityResult:
    """
    Wrapper that returns EligibilityResult schema.
    """
    result = check_eligibility(user_profile, scheme)
    return EligibilityResult(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        eligible=result["eligible"],
        reason=result["reason"],
    )
