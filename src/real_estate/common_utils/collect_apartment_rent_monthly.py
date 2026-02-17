#!/usr/bin/env python3
"""Collect apartment rent data by month and save JSON files.

Default target in this project:
- region_code: 11740 (Seoul Gangdong-gu)
- months: 202207..202601
- output: gitignore/assets/data/apartment_rent/11740/YYYYMM.json
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
    sy, sm = int(start_yyyymm[:4]), int(start_yyyymm[4:])
    ey, em = int(end_yyyymm[:4]), int(end_yyyymm[4:])
    if (sy, sm) > (ey, em):
        raise ValueError("start must be <= end")

    out: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


async def _collect_one(
    region_code: str,
    year_month: str,
    num_of_rows: int,
    out_dir: Path,
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

    out_file = out_dir / f"{year_month}.json"
    out_file.write_text(
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
        file=str(out_file),
    )


async def _run(args: argparse.Namespace) -> int:
    months = _iter_year_months(args.start, args.end)
    out_dir = Path(args.output_root) / "apartment_rent" / args.region_code
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[MonthResult] = []
    for ym in months:
        r = await _collect_one(
            region_code=args.region_code,
            year_month=ym,
            num_of_rows=args.num_of_rows,
            out_dir=out_dir,
        )
        results.append(r)
        status = "OK" if r.ok else "ERR"
        print(f"[{status}] {ym} total={r.total_count} sample={r.sample_count} msg={r.message}")

    index_path = out_dir / "index.json"
    index_payload = {
        "region_code": args.region_code,
        "start": args.start,
        "end": args.end,
        "num_of_rows": args.num_of_rows,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "results": [asdict(r) for r in results],
    }
    index_path.write_text(json.dumps(index_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Index written: {index_path}")

    failed = [r for r in results if not r.ok]
    if failed:
        print(f"Completed with failures: {len(failed)} / {len(results)}")
        return 1
    print(f"Completed successfully: {len(results)} months")
    return 0


def main() -> int:
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
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
