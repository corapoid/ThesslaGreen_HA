"""Verify version checks, release notes, deterministic archives and exclusions."""

import hashlib
import json
from zipfile import ZipFile

import pytest

from scripts.build_release import build_release


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "repository"
    integration = root / "custom_components" / "thessla_green"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text(json.dumps({"domain": "thessla_green", "version": "0.3.0"}))
    (integration / "__init__.py").write_text("# integration\n")
    (integration / "__pycache__").mkdir()
    (integration / "__pycache__" / "cached.pyc").write_bytes(b"cache")
    (integration / ".env").write_text("TEST_PLACEHOLDER\n")
    (root / "README.md").write_text("[English](README.en.md)\n")
    (root / "README.en.md").write_text("[Polski](README.md)\n")
    (root / "LICENSE").write_text("MIT License\n")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\nFuture changes\n\n"
        "## [0.3.0] - 2026-10-08\n\n### Added\n\n- Device profiles.\n\n"
        "## [0.2.5]\n\n- Older changes.\n"
    )
    return root


def test_archive_notes_checksum_and_determinism(repository, tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = build_release(repository, "v0.3.0", first_dir)
    second = build_release(repository, "v0.3.0", second_dir)
    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as bundle:
        assert bundle.testzip() is None
        assert set(bundle.namelist()) == {
            "README.md", "README.en.md", "CHANGELOG.md", "LICENSE",
            "custom_components/thessla_green/manifest.json",
            "custom_components/thessla_green/__init__.py",
        }
        assert bundle.getinfo("README.md").date_time == (1980, 1, 1, 0, 0, 0)
        assert json.loads(bundle.read("custom_components/thessla_green/manifest.json"))["version"] == "0.3.0"
    notes = (first_dir / "RELEASE_NOTES.md").read_text()
    assert "Device profiles" in notes
    assert "Future changes" not in notes and "Older changes" not in notes
    assert (first_dir / "SHA256SUMS").read_text() == f"{hashlib.sha256(first.read_bytes()).hexdigest()}  {first.name}\n"


def test_tag_version_mismatch(repository, tmp_path):
    with pytest.raises(ValueError, match="does not match manifest"):
        build_release(repository, "v0.4.0", tmp_path / "dist")


@pytest.mark.parametrize("tag", ["../v0.3.0", "v0.3.0/other", "0.3.0", "v0.3.0;command", "v00.3.0"])
def test_invalid_tag(repository, tmp_path, tag):
    with pytest.raises(ValueError, match="Invalid release tag"):
        build_release(repository, tag, tmp_path / "dist")


def test_missing_changelog_section(repository, tmp_path):
    (repository / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n")
    with pytest.raises(ValueError, match="Missing changelog section"):
        build_release(repository, "v0.3.0", tmp_path / "dist")


def test_missing_document(repository, tmp_path):
    (repository / "README.en.md").unlink()
    with pytest.raises(ValueError, match="Missing release document"):
        build_release(repository, "v0.3.0", tmp_path / "dist")


def test_missing_license(repository, tmp_path):
    (repository / "LICENSE").unlink()
    with pytest.raises(ValueError, match="Missing release document: LICENSE"):
        build_release(repository, "v0.3.0", tmp_path / "dist")
