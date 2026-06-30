"""Output validation utilities.

Provides `OutputValidator` to validate dict outputs against a schema.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class OutputValidator:
    """Validate an output dict against a simple schema.

    Schema format examples:

    - {'name': str, 'emails': list, 'age': int}
    - {'location': {'city': str, 'country': str}, 'skills': [str]}

    Expected schema values may be Python types, nested dicts, or lists
    where a single-item list denotes the element type.
    """

    def __init__(self, schema: Dict[str, Any], required: Optional[List[str]] = None) -> None:
        self.schema = schema
        self.required = required or []
        self.errors: List[str] = []

    def validate(self, output: Dict[str, Any]) -> bool:
        self.errors = []
        # required fields
        for key in self.required:
            if key not in output:
                self.errors.append(f"Missing required field: {key}")

        # type checks
        for key, expected in self.schema.items():
            if key not in output:
                continue
            val = output[key]
            if not self._match_type(val, expected):
                self.errors.append(f"Field '{key}' expected {self._expected_repr(expected)}, got {type(val).__name__}")

        return not self.errors

    def _expected_repr(self, expected: Any) -> str:
        if isinstance(expected, type):
            return expected.__name__
        if isinstance(expected, dict):
            return "object"
        if isinstance(expected, list):
            if expected:
                return f"list[{self._expected_repr(expected[0])}]"
            return "list"
        return str(expected)

    def _match_type(self, value: Any, expected: Any) -> bool:
        # accept None for any field (use required to enforce presence)
        if value is None:
            return True

        # No type constraint specified for this field (e.g. an untyped
        # custom-config field) - presence is enforced via `required`,
        # but we don't reject any value type here.
        if expected is None:
            return True

        if isinstance(expected, type):
            return isinstance(value, expected)

        if isinstance(expected, dict):
            if not isinstance(value, dict):
                return False
            # validate nested keys exist and types
            for k, exp in expected.items():
                if k not in value:
                    continue
                if not self._match_type(value[k], exp):
                    return False
            return True

        if isinstance(expected, list):
            if not isinstance(value, list):
                return False
            if not expected:
                return True
            # single-type list
            elem_type = expected[0]
            for item in value:
                if not self._match_type(item, elem_type):
                    return False
            return True

        # fallback: try to compare type names
        try:
            return isinstance(value, expected)
        except Exception:
            return False

    def get_errors(self) -> List[str]:
        return list(self.errors)
