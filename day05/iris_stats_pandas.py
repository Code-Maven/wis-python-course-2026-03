from pathlib import Path

import pandas as pd


def main() -> None:
    csv_path = Path(__file__).with_name("iris.csv")
    df = pd.read_csv(csv_path)

    print(f"Rows: {len(df)}")
    if df.empty:
        return

    print("\nSpecies counts:")
    species_counts = df["Species"].value_counts()
    for species, count in species_counts.items():
        print(f"- {species}: {count}")

    print("\nNumeric column summary:")
    numeric_df = df.select_dtypes(include="number")
    for column in numeric_df.columns:
        values = numeric_df[column]
        print(f"- {column}")
        print(f"  min: {values.min():.2f}")
        print(f"  max: {values.max():.2f}")
        print(f"  mean: {values.mean():.2f}")
        print(f"  median: {values.median():.2f}")


if __name__ == "__main__":
    main()
