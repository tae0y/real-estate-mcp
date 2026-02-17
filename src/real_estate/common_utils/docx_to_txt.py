"""Batch-convert .docx files to side-by-side .txt files.

Default behavior writes `*.txt` next to each `*.docx` with the same base name.
This is intentionally simple so it can be used for reference-doc ingestion.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from real_estate.common_utils.docx_parser import extract_dir_to_txt


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert .docx under a directory into .txt files.")
    p.add_argument("input_dir", type=Path, help="Directory to scan (recursively) for .docx files.")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output root directory. If omitted, writes .txt next to each .docx.",
    )
    p.add_argument(
        "--pattern",
        default="**/*.docx",
        help='Glob pattern relative to input_dir (default: "**/*.docx").',
    )
    p.add_argument(
        "--encoding",
        default="utf-8",
        help='Output text encoding (default: "utf-8").',
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .txt files (default: skip if exists).",
    )
    p.add_argument(
        "--keep-empty-paragraphs",
        action="store_true",
        help="Preserve empty paragraphs as blank lines (default: drop empty paragraphs).",
    )
    return p.parse_args()


def main() -> int:
    ns = _parse_args()
    results = extract_dir_to_txt(
        ns.input_dir,
        output_dir=ns.output_dir,
        pattern=ns.pattern,
        encoding=ns.encoding,
        overwrite=ns.overwrite,
        keep_empty_paragraphs=ns.keep_empty_paragraphs,
    )

    written = [r for r in results if r.written]
    skipped = [r for r in results if not r.written]

    for r in written:
        print(f"WROTE  {r.output_path}")
    for r in skipped:
        print(f"SKIP   {r.output_path}")

    print(f"Done. written={len(written)} skipped={len(skipped)} total={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

