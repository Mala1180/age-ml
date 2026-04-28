import shutil
from pathlib import Path


def save_file(
    filename: str,
    content: str,
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


def safe_filename_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def copy_out_artifacts(out_dir: Path, destination: Path) -> None:
    if not out_dir.exists():
        return
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(out_dir, destination)
