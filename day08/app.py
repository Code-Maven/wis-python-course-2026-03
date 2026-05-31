#!/usr/bin/env python3
import os
import re
import sys
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from mp_api.client import MPRester

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Fetch API Key from environment
MP_API_KEY = os.environ.get("MP_API_KEY")

def parse_elements(elem_str: str) -> list[str]:
    """
    Intelligently parses chemical elements from a string.
    Supports comma-separated, space-separated, hyphen-separated,
    or formulas like 'TiO2' or 'LiFePO4'.
    Example: 'Li-Fe-O' -> ['Li', 'Fe', 'O']
             'TiO2'     -> ['Ti', 'O']
    """
    if not elem_str:
        return []
    
    # Use regex to find Capitalized followed by optional lowercase letters (e.g. Ti, O, Li, Fe)
    matches = re.findall(r'[A-Z][a-z]?', elem_str.strip())
    
    # Deduplicate while maintaining order
    elements = []
    seen = set()
    for el in matches:
        # Simple check for valid chemical symbols (lengths 1 or 2)
        if el not in seen and len(el) <= 2:
            seen.add(el)
            elements.append(el)
            
    return elements

@app.route('/')
def index():
    """Render the dashboard home page."""
    # Pass whether API Key is configured to the template
    has_api_key = bool(MP_API_KEY)
    return render_template('index.html', has_api_key=has_api_key)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Accepts search terms and parameters, queries Materials Project,
    and returns analytical reports, statistics, and visualization datasets.
    """
    if not MP_API_KEY:
        return jsonify({
            "success": False,
            "error": "Materials Project API key is missing. Please set MP_API_KEY in your .env file."
        }), 500

    # Get JSON payload
    data = request.get_json() or {}
    
    element_input = data.get("elements", "").strip()
    min_bg = float(data.get("min_bg", 1.5))
    max_bg = float(data.get("max_bg", 3.0))
    max_hull = float(data.get("max_hull", 0.05))
    stable_only = bool(data.get("stable_only", True))

    # Parse elements
    elements = parse_elements(element_input)
    if not elements:
        return jsonify({
            "success": False,
            "error": "No valid chemical element symbols found in input. Please enter symbols like 'Ti O', 'Li Fe', or 'TiO2'."
        }), 400

    print(f"Flask API: Querying Materials Project for elements: {elements}")
    
    try:
        # Search using MPRester
        with MPRester(MP_API_KEY) as mpr:
            results = mpr.materials.summary.search(
                elements=elements,
                fields=[
                    "material_id", 
                    "formula_pretty", 
                    "band_gap", 
                    "formation_energy_per_atom", 
                    "energy_above_hull",
                    "symmetry",
                    "volume"
                ]
            )
    except Exception as exc:
        print(f"Materials Project API error: {exc}", file=sys.stderr)
        return jsonify({
            "success": False,
            "error": f"Materials Project API Error: {str(exc)}"
        }), 502

    if not results:
        return jsonify({
            "success": False,
            "error": f"No materials found containing elements: {', '.join(elements)}. Please try another search."
        }), 444

    # Convert results to list of dicts
    data_list = []
    for doc in results:
        # Safely parse crystal system from symmetry details
        symmetry = getattr(doc, "symmetry", None)
        c_system = "Unknown"
        if symmetry:
            c_system = str(getattr(symmetry, "crystal_system", "Unknown")).capitalize()

        # Safely handle field retrieval in case they are missing
        data_list.append({
            "id": str(doc.material_id),
            "formula": getattr(doc, "formula_pretty", "N/A"),
            "band_gap": float(getattr(doc, "band_gap", 0.0) or 0.0),
            "formation_energy": float(getattr(doc, "formation_energy_per_atom", 0.0) or 0.0),
            "energy_above_hull": float(getattr(doc, "energy_above_hull", 0.0) or 0.0),
            "crystal_system": c_system,
            "volume": float(getattr(doc, "volume", 0.0) or 0.0)
        })

    # Load into DataFrame
    df = pd.DataFrame(data_list)
    total_count = len(df)

    # 1. Apply Filtering for report & display candidates
    # Formation energy must be negative for compound stability, or we can show stable only based on energy above hull
    if stable_only:
        # Stable: Formation Energy < 0 and Energy Above Hull <= max_hull
        filtered_df = df[(df['formation_energy'] < 0) & (df['energy_above_hull'] <= max_hull)]
    else:
        filtered_df = df.copy()

    # Apply Band Gap filter
    candidates_df = filtered_df[
        (filtered_df['band_gap'] >= min_bg) & 
        (filtered_df['band_gap'] <= max_bg)
    ]
    
    # Sort candidates by Formation Energy (lowest/most stable first)
    candidates_df = candidates_df.sort_values(by="formation_energy")
    
    # Calculate statistics based on the full search set
    avg_bg_all = df['band_gap'].mean()
    min_fe_all = df['formation_energy'].min()
    
    # Calculate statistics based on filtered candidates
    candidates_count = len(candidates_df)
    
    if candidates_count > 0:
        avg_bg_candidates = candidates_df['band_gap'].mean()
        min_fe_candidates = candidates_df['formation_energy'].min()
        best_candidate = candidates_df.iloc[0].to_dict()
    else:
        avg_bg_candidates = 0.0
        min_fe_candidates = 0.0
        best_candidate = None

    # Sample/limit tables entries to top 1500 to keep transmission light, but return sorted results
    table_candidates = candidates_df.head(1500).to_dict(orient="records")

    # Grouping data for a small summary chart of Crystal Systems
    crystal_system_counts = df['crystal_system'].value_counts().to_dict()
    crystal_distribution = [{"system": k, "count": int(v)} for k, v in crystal_system_counts.items()]

    # Format the scatter plot data directly to send to frontend Plotly.js
    # We will send the full raw elements so the user has the ability to view/zoom all retrieved data points,
    # with a highlighting or category flag for those that qualify as candidates!
    # This gives a beautiful context of "here is the full data space, and here are the candidates".
    plot_data = []
    
    # We can separate them into "Filtered Candidates" and "Other Materials"
    candidates_ids = set(candidates_df['id'])
    
    df['is_candidate'] = df['id'].apply(lambda x: x in candidates_ids)
    
    for _, row in df.iterrows():
        plot_data.append({
            "id": row["id"],
            "formula": row["formula"],
            "x": row["band_gap"],
            "y": row["formation_energy"],
            "color_val": row["energy_above_hull"],
            "crystal": row["crystal_system"],
            "is_candidate": row["is_candidate"]
        })

    response_payload = {
        "success": True,
        "searched_elements": elements,
        "stats": {
            "total_retrieved": total_count,
            "candidates_found": candidates_count,
            "avg_bandgap_candidates": round(float(avg_bg_candidates), 4),
            "min_formation_energy_candidates": round(float(min_fe_candidates), 4),
            "avg_bandgap_all": round(float(avg_bg_all), 4) if not np.isnan(avg_bg_all) else 0,
            "min_formation_energy_all": round(float(min_fe_all), 4) if not np.isnan(min_fe_all) else 0,
            "best_candidate": best_candidate
        },
        "crystal_distribution": crystal_distribution,
        "plot_points": plot_data,
        "candidates": table_candidates
    }

    return jsonify(response_payload)

if __name__ == '__main__':
    # Running on all interfaces (0.0.0.0) on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
