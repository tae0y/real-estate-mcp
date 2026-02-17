"""Bulk collector for monthly apartment rent open-data snapshots.

This module calls `real_estate.mcp_server.server.get_apartment_rent` month by month
and stores raw JSON payloads under an output directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from real_estate.mcp_server.server import get_apartment_rent


@dataclass
class MonthResult:
    """Collection result for one `YYYYMM` period."""

    year_month: str
    ok: bool
    total_count: int | None
    sample_count: int | None
    error: str | None
    message: str | None
    file: str | None


def _iter_year_months(start_yyyymm: str, end_yyyymm: str) -> list[str]:
    if len(start_yyyymm) != 6 or len(end_yyyymm) != 6:
        raise ValueError("start/end must be YYYYMM")

    start_year, start_month = int(start_yyyymm[:4]), int(start_yyyymm[4:])
    end_year, end_month = int(end_yyyymm[:4]), int(end_yyyymm[4:])
    if (start_year, start_month) > (end_year, end_month):
        raise ValueError("start must be <= end")

    year_months: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        year_months.append(f"{year:04d}{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return year_months


async def _collect_one(
    *,
    region_code: str,
    year_month: str,
    num_of_rows: int,
    output_dir: Path,
) -> MonthResult:
    result = await get_apartment_rent(
        region_code=region_code,
        year_month=year_month,
        num_of_rows=num_of_rows,
    )
    if "error" in result:
        return MonthResult(
            year_month=year_month,
            ok=False,
            total_count=None,
            sample_count=None,
            error=result.get("error"),
            message=result.get("message"),
            file=None,
        )

    output_file = output_dir / f"{year_month}.json"
    output_file.write_text(
        json.dumps(
            {
                "region_code": region_code,
                "year_month": year_month,
                "collected_at_utc": datetime.now(UTC).isoformat(),
                "data": result,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    summary = result.get("summary", {})
    return MonthResult(
        year_month=year_month,
        ok=True,
        total_count=result.get("total_count"),
        sample_count=summary.get("sample_count"),
        error=None,
        message=None,
        file=str(output_file),
    )


async def _run(args: argparse.Namespace) -> int:
    year_months = _iter_year_months(args.start, args.end)
    output_dir = Path(args.output_root) / "apartment_rent" / args.region_code
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[MonthResult] = []
    for year_month in year_months:
        result = await _collect_one(
            region_code=args.region_code,
            year_month=year_month,
            num_of_rows=args.num_of_rows,
            output_dir=output_dir,
        )
        results.append(result)
        status = "OK" if result.ok else "ERR"
        print(
            f"[{status}] {year_month} total={result.total_count} "
            f"sample={result.sample_count} msg={result.message}"
        )

    index_path = output_dir / "index.json"
    index_payload = {
        "region_code": args.region_code,
        "start": args.start,
        "end": args.end,
        "num_of_rows": args.num_of_rows,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "results": [asdict(result) for result in results],
    }
    index_path.write_text(json.dumps(index_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Index written: {index_path}")

    failed = [result for result in results if not result.ok]
    if failed:
        print(f"Completed with failures: {len(failed)} / {len(results)}")
        return 1

    print(f"Completed successfully: {len(results)} months")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect apartment rent data by month.")
    parser.add_argument("--region-code", default="11740", help="5-digit LAWD_CD (default: 11740)")
    parser.add_argument("--start", default="202207", help="Start month YYYYMM (default: 202207)")
    parser.add_argument("--end", default="202601", help="End month YYYYMM (default: 202601)")
    parser.add_argument(
        "--num-of-rows",
        type=int,
        default=2000,
        help="Rows per month request (default: 2000)",
    )
    parser.add_argument(
        "--output-root",
        default="gitignore/assets/data",
        help="Output root directory (default: gitignore/assets/data)",
    )
    return parser.parse_args()


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
