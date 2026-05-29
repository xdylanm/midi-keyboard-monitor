"""
Sidecar JSON I/O and schema validation.

Operations:
    load_sidecar(path)           -> AnalysisResult
    save_sidecar(result, path)   -> None
    validate_sidecar_json(obj)   -> None  (raises SidecarValidationError on failure)
"""

from __future__ import annotations

import json
import pathlib
from typing import Union

import jsonschema
import jsonschema.exceptions

from core.models import AnalysisResult

# Load the bundled schema once at import time.
_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schema" / "analysis_result.schema.json"

with _SCHEMA_PATH.open() as _f:
    _SCHEMA: dict = json.load(_f)


class SidecarValidationError(ValueError):
    """Raised when a sidecar JSON object fails schema validation."""

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors

    def __str__(self) -> str:  # pragma: no cover
        detail = "\n  - ".join(self.errors)
        return f"{super().__str__()}\n  - {detail}"


def validate_sidecar_json(obj: dict) -> None:
    """Validate a plain-dict sidecar against the AnalysisResult schema.

    Args:
        obj: Parsed sidecar dict.

    Raises:
        SidecarValidationError: If validation fails. The ``errors`` attribute
            lists human-readable messages for each violation.
    """
    validator = jsonschema.Draft7Validator(_SCHEMA)
    raw_errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    if raw_errors:
        messages = [e.message for e in raw_errors]
        raise SidecarValidationError(
            f"Sidecar validation failed with {len(messages)} error(s)",
            messages,
        )


def load_sidecar(path: Union[str, pathlib.Path]) -> AnalysisResult:
    """Read and validate a sidecar JSON file, returning an AnalysisResult.

    Args:
        path: Path to a .analysis.json sidecar file.

    Returns:
        AnalysisResult domain object.

    Raises:
        FileNotFoundError: If the file does not exist.
        SidecarValidationError: If the file content does not validate.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Sidecar file not found: {path}")

    with path.open() as f:
        obj = json.load(f)

    validate_sidecar_json(obj)
    return AnalysisResult.from_dict(obj)


def save_sidecar(
    result: AnalysisResult,
    path: Union[str, pathlib.Path],
) -> None:
    """Serialise an AnalysisResult to a JSON sidecar file.

    Serialisation is deterministic: keys are sorted and indentation is fixed
    at 2 spaces.

    Args:
        result: AnalysisResult domain object.
        path:   Destination file path.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    obj = result.to_dict()
    validate_sidecar_json(obj)

    with path.open("w") as f:
        json.dump(obj, f, sort_keys=True, indent=2)
        f.write("\n")
