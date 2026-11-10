from django.utils.dateparse import parse_date
from rest_framework.exceptions import ParseError

ADMIN_ONLY = "Admin only (is_staff)."


def params_to_ints(query_string: str) -> list[int]:
    """Convert '1,2,3' to [1, 2, 3]. Anything else is answered with 400."""
    try:
        return [int(str_id) for str_id in query_string.split(",")]
    except ValueError:
        raise ParseError(
            f"Expected a comma-separated list of integers, got '{query_string}'"
        )


def param_to_int(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ParseError({name: f"Expected an integer, got '{value}'"})


def param_to_date(value: str, name: str):
    parsed = parse_date(value)
    if parsed is None:
        raise ParseError(
            {name: f"Expected a date in YYYY-MM-DD format, got '{value}'"}
        )
    return parsed


def param_to_bool(value: str, name: str) -> bool:
    lowered = value.lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no"):
        return False
    raise ParseError({name: f"Expected a boolean value, got '{value}'"})
