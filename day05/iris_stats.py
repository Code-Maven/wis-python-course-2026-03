from collections import Counter
from pathlib import Path
import csv
import statistics


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f: 
        return list(csv.DictReader(f))


def collect_numeric_columns(rows: list[dict[str, str]]) -> dict[str, list[float]]:
    numeric_data: dict[str, list[float]] = {}
    if not rows:
        return numeric_data

    for field in rows[0].keys():
        if field == "Species":
            continue

        values: list[float] = []
        is_numeric = True
        for row in rows:
            value = row.get(field, "").strip()
            if value == "":
                is_numeric = False
                break
            try:
                values.append(float(value))
            except ValueError:
                is_numeric = False
                break

        if is_numeric:
            numeric_data[field] = values

    return numeric_data


def print_statistics(rows: list[dict[str, str]]) -> None:
    print(f"Rows: {len(rows)}")
    if not rows:
        return

    species_counts = Counter(row.get("Species", "Unknown") for row in rows)
    print("\nSpecies counts:")
    for species, count in species_counts.most_common():
        print(f"- {species}: {count}")

    numeric_data = collect_numeric_columns(rows)
    print("\nNumeric column summary:")
    for column, values in numeric_data.items():
        print(f"- {column}")
        print(f"  min: {min(values):.2f}")
        print(f"  max: {max(values):.2f}")
        print(f"  mean: {statistics.mean(values):.2f}")
        print(f"  median: {statistics.median(values):.2f}")


def main() -> None:
    csv_path = Path(__file__).with_name("iris.csv")
    rows = load_rows(csv_path)
    print_statistics(rows)


if __name__ == "__main__":
    main()
