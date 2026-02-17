# Common Utils Guide

Utility modules and CLI scripts under `src/real_estate/common_utils` for local parsing and bulk data collection.

## Files

- `docx_parser.py`: Library functions to extract text from `.docx` files
- `hwp_parser.py`: Library function to extract text from `.hwp` files
- `docx_bulk_parser.py`: CLI wrapper for batch `.docx` to `.txt` conversion
- `opendata_bulk_collector.py`: CLI tool to collect monthly apartment rent snapshots into JSON files

## Prerequisites

- Python 3.12+
- `uv` installed
- For open-data collection: valid `DATA_GO_KR_API_KEY` in environment or `.env`

## Library Usage

### DOCX Parser

```python
from real_estate.common_utils.docx_parser import extract_text, extract_dir_to_txt

text = extract_text("/path/to/file.docx")
results = extract_dir_to_txt("/path/to/input_dir", overwrite=False)
```

### HWP Parser

```python
from real_estate.common_utils.hwp_parser import extract_text

text = extract_text("/path/to/file.hwp")
```

## CLI Usage

### Batch DOCX to TXT

1. Run with default behavior (writes `.txt` next to each `.docx`).

    ```bash
    uv run python src/real_estate/common_utils/docx_bulk_parser.py /path/to/docs
    ```

1. Run with a separate output directory.

    ```bash
    uv run python src/real_estate/common_utils/docx_bulk_parser.py /path/to/docs \
      --output-dir /path/to/output \
      --overwrite
    ```

### Open Data Monthly Collector

1. Collect apartment rent data for a region and month range.

    ```bash
    uv run python src/real_estate/common_utils/opendata_bulk_collector.py \
      --region-code 11740 \
      --start 202401 \
      --end 202412 \
      --num-of-rows 2000
    ```

1. Output is written under:

    ```text
    gitignore/assets/data/apartment_rent/<region_code>/
    ```

    Includes one `<YYYYMM>.json` file per month and `index.json` summary.

## Notes

- All modules follow snake_case naming and explicit type hints.
- `docx_bulk_parser.py` and `opendata_bulk_collector.py` are CLI entry scripts; parser logic stays in `docx_parser.py` and `hwp_parser.py`.
- If API calls fail in `opendata_bulk_collector.py`, failures are recorded in `index.json` and the process exits with code `1`.
