"""
Core data models for M1.

MidiEvent is the canonical normalized representation of a single MIDI message.
AnalysisResult is the M1 placeholder for per-session accuracy results.
AppConfig is the application configuration model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# MidiEvent
# ---------------------------------------------------------------------------

MIDI_EVENT_TYPES = frozenset(
    {"note_on", "note_off", "control_change", "program_change", "pitch_bend", "other"}
)


@dataclass
class MidiEvent:
    """Normalized representation of a single MIDI message."""

    type: str                        # one of MIDI_EVENT_TYPES
    channel: int                     # 0-15
    note: Optional[int]              # 0-127; None for non-note events
    velocity: Optional[int]          # 0-127; None for non-note events
    timestamp_ticks: int             # raw tick offset from track start
    timestamp_ms: float = 0.0       # derived when tempo context exists

    def __post_init__(self) -> None:
        if self.type not in MIDI_EVENT_TYPES:
            raise ValueError(f"Invalid MIDI event type: {self.type!r}")
        if not (0 <= self.channel <= 15):
            raise ValueError(f"Channel must be 0-15, got {self.channel}")
        if self.note is not None and not (0 <= self.note <= 127):
            raise ValueError(f"Note must be 0-127, got {self.note}")
        if self.velocity is not None and not (0 <= self.velocity <= 127):
            raise ValueError(f"Velocity must be 0-127, got {self.velocity}")

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "channel": self.channel,
            "note": self.note,
            "velocity": self.velocity,
            "timestamp_ticks": self.timestamp_ticks,
            "timestamp_ms": self.timestamp_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MidiEvent":
        return cls(
            type=data["type"],
            channel=data["channel"],
            note=data.get("note"),
            velocity=data.get("velocity"),
            timestamp_ticks=data["timestamp_ticks"],
            timestamp_ms=data.get("timestamp_ms", 0.0),
        )


# ---------------------------------------------------------------------------
# AnalysisResult  (M1 placeholder shape)
# ---------------------------------------------------------------------------

@dataclass
class NoteSummary:
    """Per-note entry in an AnalysisResult (M1: empty / placeholder)."""
    note: Optional[int] = None
    onset_ms: Optional[float] = None
    duration_ms: Optional[float] = None
    velocity: Optional[int] = None


@dataclass
class AnalysisSummary:
    """Aggregate summary fields (M1: all nullable)."""
    note_accuracy: Optional[float] = None
    rhythm_accuracy: Optional[float] = None
    dynamics_accuracy: Optional[float] = None


@dataclass
class AnalysisResult:
    """M1 placeholder for per-session accuracy results."""

    schema_version: str
    performance_id: str
    score_ref: str
    recorded_at: str                      # ISO-8601
    notes: list[NoteSummary] = field(default_factory=list)
    summary: AnalysisSummary = field(default_factory=AnalysisSummary)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "performance_id": self.performance_id,
            "score_ref": self.score_ref,
            "recorded_at": self.recorded_at,
            "notes": [
                {
                    "note": n.note,
                    "onset_ms": n.onset_ms,
                    "duration_ms": n.duration_ms,
                    "velocity": n.velocity,
                }
                for n in self.notes
            ],
            "summary": {
                "note_accuracy": self.summary.note_accuracy,
                "rhythm_accuracy": self.summary.rhythm_accuracy,
                "dynamics_accuracy": self.summary.dynamics_accuracy,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        notes = [
            NoteSummary(
                note=n.get("note"),
                onset_ms=n.get("onset_ms"),
                duration_ms=n.get("duration_ms"),
                velocity=n.get("velocity"),
            )
            for n in data.get("notes", [])
        ]
        raw_summary = data.get("summary", {}) or {}
        summary = AnalysisSummary(
            note_accuracy=raw_summary.get("note_accuracy"),
            rhythm_accuracy=raw_summary.get("rhythm_accuracy"),
            dynamics_accuracy=raw_summary.get("dynamics_accuracy"),
        )
        return cls(
            schema_version=data["schema_version"],
            performance_id=data["performance_id"],
            score_ref=data["score_ref"],
            recorded_at=data["recorded_at"],
            notes=notes,
            summary=summary,
        )


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------

@dataclass
class DefaultPaths:
    scores: str = "scores"
    performances: str = "performances"


@dataclass
class MappingDefaults:
    """Placeholder for future mapping defaults."""
    pitch_split: int = 60   # MIDI 60 = C4


@dataclass
class AppConfig:
    """Application configuration."""

    schema_version: str
    default_paths: DefaultPaths = field(default_factory=DefaultPaths)
    logging_level: str = "INFO"
    mapping_defaults: MappingDefaults = field(default_factory=MappingDefaults)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "default_paths": {
                "scores": self.default_paths.scores,
                "performances": self.default_paths.performances,
            },
            "logging_level": self.logging_level,
            "mapping_defaults": {
                "pitch_split": self.mapping_defaults.pitch_split,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        raw_paths = data.get("default_paths", {})
        raw_mapping = data.get("mapping_defaults", {})
        return cls(
            schema_version=data["schema_version"],
            default_paths=DefaultPaths(
                scores=raw_paths.get("scores", "scores"),
                performances=raw_paths.get("performances", "performances"),
            ),
            logging_level=data.get("logging_level", "INFO"),
            mapping_defaults=MappingDefaults(
                pitch_split=raw_mapping.get("pitch_split", 60),
            ),
        )
