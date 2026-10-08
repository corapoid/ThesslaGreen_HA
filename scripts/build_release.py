"""Build a version-checked release archive, checksum and changelog notes."""

import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

TAG_PATTERN = re.compile(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?")
DOCUMENTS = ("README.md", "README.en.md", "CHANGELOG.md", "LICENSE")


def release_notes(changelog: str, version: str) -> str:
    """Extract exactly one released version; do not publish Unreleased notes."""
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n", changelog, flags=re.MULTILINE)
    if match is None:
        raise ValueError(f"Missing changelog section for {version}")
    lines = []
    for line in changelog[match.end():].splitlines():
        if line.startswith("## ") or re.match(r"^\[[^\]]+\]:", line):
            break
        lines.append(line)
    notes = "\n".join(lines).strip()
    if not notes:
        raise ValueError(f"Empty changelog section for {version}")
    return notes + "\n"


def build_release(repository_root: Path, tag: str, output_dir: Path) -> Path:
    if TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError(f"Invalid release tag: {tag}")
    integration = repository_root / "custom_components" / "thessla_green"
    manifest = json.loads((integration / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("domain") != "thessla_green":
        raise ValueError("Unexpected integration domain")
    if tag != f"v{manifest.get('version')}":
        raise ValueError(f"Release tag {tag} does not match manifest version {manifest.get('version')}")
    for name in DOCUMENTS:
        if not (repository_root / name).is_file():
            raise ValueError(f"Missing release document: {name}")
    notes = release_notes((repository_root / "CHANGELOG.md").read_text(encoding="utf-8"), tag[1:])
    files = [(repository_root / name, name) for name in DOCUMENTS]
    for path in integration.rglob("*"):
        relative = path.relative_to(integration)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlinks are not supported in release archives: {relative}")
        if path.is_file() and path.suffix not in (".pyc", ".pyo"):
            files.append((path, path.relative_to(repository_root).as_posix()))
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"thessla_green_{tag}.zip"
    temporary = archive.with_suffix(".zip.tmp")
    with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as bundle:
        for source, name in sorted(files, key=lambda item: item[1]):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(temporary) as bundle:
        if damaged := bundle.testzip():
            raise ValueError(f"Invalid release archive member: {damaged}")
        for name in bundle.namelist():
            if name.endswith(".json"):
                json.loads(bundle.read(name))
    temporary.replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output_dir / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    (output_dir / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    try:
        archive = build_release(Path(__file__).resolve().parents[1], args.tag, args.output_dir)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Release build failed: {error}\n")
    print(f"Validated release archive: {archive}")


if __name__ == "__main__":
    main()
