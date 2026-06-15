"""Company email domain rules for Sportify factory accounts."""
from fastapi import HTTPException, status

ALLOWED_EMAIL_DOMAINS = frozenset({"sportify.com"})


def assert_company_email(email: str) -> str:
    """Return normalized email or raise ValueError if domain is not allowed."""
    normalized = email.strip().lower()
    if "@" not in normalized:
        raise ValueError("Invalid email address.")
    domain = normalized.rsplit("@", 1)[1]
    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise ValueError(
            "Only @sportify.com company emails are allowed. "
            "Personal addresses like @gmail.com cannot be used."
        )
    return normalized


def validate_company_email(email: str) -> str:
    """Return normalized email or raise HTTPException if domain is not allowed."""
    try:
        return assert_company_email(email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
