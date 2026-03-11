#!/usr/bin/env python3

import argparse
import shutil
import zipfile
from pathlib import Path


def write_manifest(path: Path, nar_id: str, nar_group: str, nar_version: str) -> None:
    content = "\n".join(
        [
            "Manifest-Version: 1.0",
            "Created-By: upstream-repro",
            f"Nar-Id: {nar_id}",
            f"Nar-Group: {nar_group}",
            f"Nar-Version: {nar_version}",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def build_archive(unpack_dir: Path, output_nar: Path) -> None:
    output_nar.parent.mkdir(parents=True, exist_ok=True)
    if output_nar.exists():
        output_nar.unlink()

    with zipfile.ZipFile(output_nar, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(unpack_dir.rglob("*")):
            archive.write(path, path.relative_to(unpack_dir))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a minimal Python NAR for reproducing NiFi bridge startup issues."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("upstream-repro/processors"),
        help="Directory containing synthetic processor modules",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("upstream-repro/dist/py4j-repro-python-extensions.nar"),
        help="Output NAR path",
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path(".build/upstream-repro-nar"),
        help="Temporary build directory",
    )
    parser.add_argument("--nar-id", default="py4j-repro-python-extensions")
    parser.add_argument("--nar-group", default="repro")
    parser.add_argument("--nar-version", default="1.0.0")
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_nar = args.output.resolve()
    build_dir = args.build_dir.resolve()
    unpack_dir = build_dir / "unpacked"
    processors_dir = unpack_dir / "processors"
    manifest_path = unpack_dir / "META-INF" / "MANIFEST.MF"
    bundled_dir = unpack_dir / "NAR-INF" / "bundled-dependencies"

    if not source_dir.exists():
        raise SystemExit(f"Processor source directory not found: {source_dir}")

    if build_dir.exists():
        shutil.rmtree(build_dir)

    processors_dir.mkdir(parents=True, exist_ok=True)
    bundled_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    for path in sorted(source_dir.rglob("*.py")):
        target = processors_dir / path.relative_to(source_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    write_manifest(manifest_path, args.nar_id, args.nar_group, args.nar_version)
    build_archive(unpack_dir, output_nar)

    print(f"Built {output_nar}")
    print("Modules:")
    for path in sorted(source_dir.rglob("*.py")):
        print(f"  {path.relative_to(source_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
