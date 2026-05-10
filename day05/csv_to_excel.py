import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read a CSV file and save it as an Excel file."
    )
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument(
        "excel_file",
        nargs="?",
        help="Optional output Excel file path (default: same name as CSV with .xlsx)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists() or not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if args.excel_file:
        excel_path = Path(args.excel_file)
    else:
        excel_path = csv_path.with_suffix(".xlsx")

    data = pd.read_csv(csv_path)
    data.to_excel(excel_path, index=False)

    print(f"Saved Excel file: {excel_path}")


if __name__ == "__main__":
    main()
