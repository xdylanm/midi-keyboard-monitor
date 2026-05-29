"""
MusicXML I/O using music21.

Operations:
    load_musicxml(path)         -> music21.stream.Score
    save_musicxml(score, path)  -> None
"""

from __future__ import annotations

import pathlib
from typing import Union

import music21.converter
import music21.stream


def load_musicxml(path: Union[str, pathlib.Path]) -> music21.stream.Score:
    """Parse a MusicXML file and return a music21 Score object.

    Args:
        path: Path to a .musicxml or .mxl file.

    Returns:
        Parsed music21.stream.Score.

    Raises:
        FileNotFoundError: If the file does not exist.
        music21.converter.ConverterException: If parsing fails.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MusicXML file not found: {path}")
    score = music21.converter.parse(str(path))
    if not isinstance(score, music21.stream.Score):
        # converter may return a generic Stream for single-part files
        score = score.makeNotation()
        if not isinstance(score, music21.stream.Score):
            wrapped = music21.stream.Score()
            wrapped.append(score)
            score = wrapped
    return score


def save_musicxml(
    score: music21.stream.Score,
    path: Union[str, pathlib.Path],
) -> None:
    """Write a music21 Score to a MusicXML file.

    Args:
        score: The music21 Score to serialise.
        path:  Destination file path (.musicxml).
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(path))
