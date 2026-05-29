"""
Test Group C: Sidecar schema validation tests.

Fixtures under tests/m1/fixtures/:
- valid_sidecar.json              - passes validation
- invalid_missing_schema_version.json   - fails: missing required field
- invalid_extra_field.json        - fails: additional property not allowed

Assertions:
- Valid sidecar passes schema validation.
- Missing required fields fail with explicit field names in error messages.
- Additional unexpected fields fail when additionalProperties is false.
"""

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from core.io.sidecar_io import (
    load_sidecar,
    save_sidecar,
    validate_sidecar_json,
    SidecarValidationError,
)
from core.models import AnalysisResult, AnalysisSummary
from tests.m1.helpers import local_fixture_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fixture(name: str) -> dict:
    path = local_fixture_path(name)
    with path.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test Group C: Schema validation
# ---------------------------------------------------------------------------

def test_valid_sidecar_passes_validation():
    """Valid sidecar fixture passes schema validation without raising."""
    obj = load_fixture("valid_sidecar.json")
    validate_sidecar_json(obj)  # must not raise


def test_missing_schema_version_fails_validation():
    """Sidecar missing schema_version must fail validation."""
    obj = load_fixture("invalid_missing_schema_version.json")
    with pytest.raises(SidecarValidationError) as exc_info:
        validate_sidecar_json(obj)
    # Error message must mention the missing field
    error_text = " ".join(exc_info.value.errors)
    assert "schema_version" in error_text, (
        f"Expected 'schema_version' in error messages, got: {exc_info.value.errors}"
    )


def test_extra_field_fails_validation():
    """Sidecar with an unknown field must fail when additionalProperties is false."""
    obj = load_fixture("invalid_extra_field.json")
    with pytest.raises(SidecarValidationError) as exc_info:
        validate_sidecar_json(obj)
    # Error message must mention additional properties
    error_text = " ".join(exc_info.value.errors).lower()
    assert "additional" in error_text or "unknown_field" in error_text, (
        f"Expected additional-property error, got: {exc_info.value.errors}"
    )


# ---------------------------------------------------------------------------
# Load / save round-trip
# ---------------------------------------------------------------------------

def test_load_sidecar_returns_analysis_result():
    """load_sidecar returns an AnalysisResult domain object."""
    path = local_fixture_path("valid_sidecar.json")
    result = load_sidecar(path)
    assert isinstance(result, AnalysisResult)


def test_load_sidecar_preserves_fields():
    """Loaded AnalysisResult fields match fixture values."""
    path = local_fixture_path("valid_sidecar.json")
    result = load_sidecar(path)
    assert result.schema_version == "1.0"
    assert result.performance_id == "perf-001"
    assert result.score_ref == "scores/Cmaj.musicxml"
    assert result.recorded_at == "2026-05-28T12:00:00Z"
    assert len(result.notes) == 2
    assert result.notes[0].note == 60
    assert result.notes[1].note == 62


def test_save_and_reload_sidecar():
    """Save an AnalysisResult and reload it; fields must match."""
    result = AnalysisResult(
        schema_version="1.0",
        performance_id="perf-rt-test",
        score_ref="scores/test.musicxml",
        recorded_at="2026-05-28T10:00:00Z",
        notes=[],
        summary=AnalysisSummary(note_accuracy=None, rhythm_accuracy=None, dynamics_accuracy=None),
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)

    save_sidecar(result, tmp_path)
    reloaded = load_sidecar(tmp_path)
    tmp_path.unlink(missing_ok=True)

    assert reloaded.schema_version == result.schema_version
    assert reloaded.performance_id == result.performance_id
    assert reloaded.score_ref == result.score_ref
    assert reloaded.recorded_at == result.recorded_at
    assert reloaded.notes == result.notes


def test_save_sidecar_deterministic():
    """Saving the same AnalysisResult twice produces byte-identical files."""
    result = AnalysisResult(
        schema_version="1.0",
        performance_id="perf-det",
        score_ref="scores/test.musicxml",
        recorded_at="2026-05-28T09:00:00Z",
        notes=[],
        summary=AnalysisSummary(),
    )
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t1:
        path1 = pathlib.Path(t1.name)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as t2:
        path2 = pathlib.Path(t2.name)

    save_sidecar(result, path1)
    save_sidecar(result, path2)

    content1 = path1.read_text()
    content2 = path2.read_text()
    path1.unlink(missing_ok=True)
    path2.unlink(missing_ok=True)

    assert content1 == content2, "Saved sidecar content is not deterministic"


def test_load_nonexistent_sidecar_raises():
    """load_sidecar raises FileNotFoundError for a missing file."""
    with pytest.raises(FileNotFoundError):
        load_sidecar("/nonexistent/path/analysis.json")


def test_validate_multiple_missing_fields():
    """Missing multiple required fields should report each one."""
    obj = {"schema_version": "1.0"}  # missing performance_id, score_ref, recorded_at, notes, summary
    with pytest.raises(SidecarValidationError) as exc_info:
        validate_sidecar_json(obj)
    # Should have multiple errors
    assert len(exc_info.value.errors) > 1, "Expected multiple validation errors"
