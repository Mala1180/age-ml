"""Generated code must retain its checksum on Windows and Unix."""

import hashlib
from pathlib import Path

import pytest

from ageml.common.utils import save_file
from ageml.protocol import file_hash


@pytest.mark.parametrize("platform_newline", ["\n", "\r\n"])
def test_generated_code_hash_matches_saved_artifact(
    tmp_path, monkeypatch, platform_newline
):
    original_write_text = Path.write_text

    def platform_write_text(path, data, encoding=None, errors=None, newline=None):
        # Emulate the platform's text-mode default even on a Linux test runner.
        return original_write_text(
            path,
            data,
            encoding=encoding,
            errors=errors,
            newline=platform_newline if newline is None else newline,
        )

    monkeypatch.setattr(Path, "write_text", platform_write_text)
    code = "# Pipeline générée\ndef build_model(X_train, y_train):\n    return None\n"
    artifact = save_file("code.py", code, tmp_path / "pipeline_0")
    assert artifact.read_bytes() == code.encode("utf-8")
    assert file_hash(artifact) == hashlib.sha256(code.encode("utf-8")).hexdigest()
