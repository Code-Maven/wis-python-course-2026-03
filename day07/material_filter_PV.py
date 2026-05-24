#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from mp_api.client import MPRester

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch materials data from Materials Project API, filter for stability and band gap, and plot."
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="Your Materials Project API key (required)",
    )
    parser.add_argument(
        "--elements",
        nargs="+",
        default=["Ti", "O"],
        help="Elements to search for separated by spaces (default: Ti O)",
    )
    parser.add_argument(
        "--min-bg",
        type=float,
        default=1.5,
        help="Minimum band gap in eV (default: 1.5)",
    )
    parser.add_argument(
        "--max-bg",
        type=float,
        default=3.0,
        help="Maximum band gap in eV (default: 3.0)",
    )
    parser.add_argument(
        "--output",
        help="Optional output image path. If omitted, the graph is shown on screen.",
    )
    return parser.parse_args()


def fetch_materials_data(api_key: str, elements: list[str]) -> pd.DataFrame:
    """Download material data from the MP database based on elements."""
    print(f"Connecting to Materials Project for elements: {', '.join(elements)}...")
    
    try:
        with MPRester(api_key) as mpr:
            results = mpr.materials.summary.search(
                elements=elements,
                fields=["material_id", "formula_pretty", "band_gap", "formation_energy_per_atom", "energy_above_hull"]
            )
    except Exception as exc:
        print(f"API Error: {exc}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Successfully downloaded data for {len(results)} materials.")
    
    # Convert to Pandas DataFrame
    data = [
        {
            "ID": doc.material_id,
            "Formula": doc.formula_pretty,
            "Band_Gap_eV": doc.band_gap,
            "Formation_Energy": doc.formation_energy_per_atom,
            "Energy_Above_Hull": doc.energy_above_hull
        }
        for doc in results
    ]
    return pd.DataFrame(data)


def filter_solar_candidates(df: pd.DataFrame, min_bg: float, max_bg: float) -> pd.DataFrame:
    """Filter the dataframe for thermodynamic stability and target band gap."""
    print("Filtering for thermodynamically stable candidates within the target band gap...")
    
    # Must be thermodynamically stable (Formation Energy < 0, Energy Above Hull near 0)
    stable_df = df[(df['Formation_Energy'] < 0) & (df['Energy_Above_Hull'] <= 0.05)]
    
    # Apply user-defined band gap limits
    candidates = stable_df[(stable_df['Band_Gap_eV'] >= min_bg) & (stable_df['Band_Gap_eV'] <= max_bg)]
    
    # Sort so the most stable are at the top
    return candidates.sort_values(by="Formation_Energy")


def main() -> None:
    args = parse_args()

    # 1. Fetch
    df = fetch_materials_data(args.api_key, args.elements)
    if df.empty:
        print("No materials found.")
        return

    # 2. Process
    candidates = filter_solar_candidates(df, args.min_bg, args.max_bg)
    
    print(f"\nFound {len(candidates)} promising candidates!")
    if not candidates.empty:
        print("Top 5 candidates:")
        print(candidates[['Formula', 'Band_Gap_eV', 'Formation_Energy']].head())

    # 3. Visualize
    print("\nGenerating plot...")
    plt.scatter(
        candidates['Band_Gap_eV'], 
        candidates['Formation_Energy'], 
        c=candidates['Energy_Above_Hull'],
        cmap='viridis', 
        alpha=0.8, 
        edgecolors='w', 
        s=100
    )
    
    plt.colorbar(label='Energy Above Hull (eV/atom) - Lower is more stable')
    plt.title(f"Material Screener: {'-'.join(args.elements)} Compounds", fontsize=14)
    plt.xlabel('Band Gap (eV)', fontsize=12)
    plt.ylabel('Formation Energy (eV/atom)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)

    # 4. Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches="tight")
        print(f"Saved graph: {output_path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()