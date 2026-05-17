#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot iris petal measurements from a CSV file."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "day05" / "iris.csv"),
        help="Path to the input CSV file (default: day05/iris.csv)",
    )
    parser.add_argument(
        "--output",
        help="Optional output image path. If omitted, the graph is shown on screen.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists() or not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    required_columns = {"PetalLengthCm", "PetalWidthCm", "Species"}

    data = pd.read_csv(csv_path)
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV file is missing required columns: {missing_text}")

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required to draw the graph. Install it with: pip install matplotlib"
        ) from exc

    colors = {
        "Iris-setosa": "red",
        "Iris-versicolor": "green",
        "Iris-virginica": "blue",
    }

    for species, group in data.groupby("Species"):
        plt.scatter(
            group["PetalLengthCm"],
            group["PetalWidthCm"],
            label=species,
            color=colors.get(species),
        )

    plt.xlabel("Petal length (cm)")
    plt.ylabel("Petal width (cm)")
    plt.title("Iris flowers")
    plt.legend()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight")
        print(f"Saved graph: {output_path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
