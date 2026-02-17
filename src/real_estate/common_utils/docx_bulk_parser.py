"""Bulk conversion helper for extracting .txt files from .docx files.

This module wraps `real_estate.common_utils.docx_parser.extract_dir_to_txt`
with a small CLI interface for batch processing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from real_estate.common_utils.docx_parser import extract_dir_to_txt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert .docx files under a directory into .txt files.")
    parser.add_argument("input_dir", type=Path, help="Directory to scan (recursively) for .docx files.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output root directory. If omitted, writes .txt next to each .docx.",
    )
    parser.add_argument(
        "--pattern",
        default="**/*.docx",
        help='Glob pattern relative to input_dir (default: "**/*.docx").',
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help='Output text encoding (default: "utf-8").',
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .txt files (default: skip if exists).",
    )
    parser.add_argument(
        "--keep-empty-paragraphs",
        action="store_true",
        help="Preserve empty paragraphs as blank lines (default: drop empty paragraphs).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    results = extract_dir_to_txt(
        args.input_dir,
        output_dir=args.output_dir,
        pattern=args.pattern,
        encoding=args.encoding,
        overwrite=args.overwrite,
        keep_empty_paragraphs=args.keep_empty_paragraphs,
    )

    written = [result for result in results if result.written]
    skipped = [result for result in results if not result.written]

    for result in written:
        print(f"WROTE  {result.output_path}")
    for result in skipped:
        print(f"SKIP   {result.output_path}")

    print(f"Done. written={len(written)} skipped={len(skipped)} total={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
