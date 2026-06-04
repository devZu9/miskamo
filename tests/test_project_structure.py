"""Tests for project structure — prevent path resolution bugs on file moves."""

from pathlib import Path


def test_audio2midi_ddsp_path_pattern():
    """core/audio2midi.py must resolve DDSP path relative to project root (not its own dir)."""
    src = Path(__file__).resolve().parent.parent / "core" / "audio2midi.py"
    text = src.read_text(encoding="utf-8")
    found = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ROOT") and "Path" in stripped and "DDSP" in stripped:
            assert ".parent.parent" in stripped, (
                f"ROOT must go up 2 levels (project root):\n  {stripped}"
            )
            assert ".resolve()" in stripped, (
                f"ROOT must use .resolve() for correct __file__ resolution:\n  {stripped}"
            )
            assert "DDSP-Timbre-Transfer" in stripped
            found = True
            break
    assert found, "Could not find ROOT = Path(...) with DDSP path in core/audio2midi.py"


def test_core_file_project_root_resolution():
    """A file in core/ using parent.parent should resolve to project root."""
    fake_core = Path(__file__).resolve().parent.parent / "core" / "audio2midi.py"
    assert fake_core.exists(), f"Expected core file at {fake_core}"
    computed_project = fake_core.resolve().parent.parent
    actual_project = Path(__file__).resolve().parent.parent
    assert computed_project == actual_project, (
        f"core/ file computed project root as {computed_project}, "
        f"expected {actual_project}"
    )
