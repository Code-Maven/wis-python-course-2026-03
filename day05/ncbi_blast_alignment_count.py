#!/usr/bin/env python3
"""
Search NCBI Nucleotide for a term, then run BLAST for each sequence and
report how many alignments were found.

Requires Biopython:
    pip install biopython

Example:
    python ncbi_blast_alignment_count.py "influenza a virus hemagglutinin" --email you@example.com --max-seqs 3
"""

from __future__ import annotations

import argparse
import io
import sys
from urllib.error import HTTPError

from Bio import Entrez, SeqIO
from Bio.Blast import NCBIWWW, NCBIXML


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search NCBI Nucleotide by term and count BLAST alignments for each result."
        )
    )
    parser.add_argument("term", help="Search term for the NCBI nucleotide database")
    parser.add_argument(
        "--email",
        required=True,
        help="Your email address (required by NCBI for API access)",
    )
    parser.add_argument(
        "--max-seqs",
        type=int,
        default=3,
        help="Maximum number of sequences to fetch from the search results (default: 3)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional NCBI API key to increase request rate limits",
    )
    parser.add_argument(
        "--blast-db",
        default="nt",
        help="BLAST database to search against (default: nt)",
    )
    return parser.parse_args()


def search_nucleotide_ids(term: str, max_seqs: int) -> list[str]:
    """Return a list of NCBI nucleotide record IDs matching the search term."""
    handle = Entrez.esearch(db="nucleotide", term=term, retmax=max_seqs)
    search_results = Entrez.read(handle)
    handle.close()
    return list(search_results["IdList"])


def fetch_sequences(ids: list[str]) -> list[SeqIO.SeqRecord]:
    """Fetch FASTA sequences from NCBI for the given list of IDs."""
    handle = Entrez.efetch(
        db="nucleotide",
        id=",".join(ids),
        rettype="fasta",
        retmode="text",
    )
    fasta_text = handle.read()
    handle.close()

    # Use SeqIO to parse the FASTA-formatted text
    records = list(SeqIO.parse(io.StringIO(fasta_text), "fasta"))
    return records


def count_alignments(record: SeqIO.SeqRecord, blast_db: str) -> int:
    """Submit a sequence to NCBI BLAST and return the number of alignments found."""
    # NCBIWWW.qblast submits the job and waits for results automatically
    result_handle = NCBIWWW.qblast(
        program="blastn",
        database=blast_db,
        sequence=str(record.seq),
    )

    # NCBIXML.read parses the XML result into a structured record
    blast_record = NCBIXML.read(result_handle)
    result_handle.close()

    return len(blast_record.alignments)


def main() -> None:
    args = parse_args()

    if args.max_seqs <= 0:
        print("--max-seqs must be greater than 0", file=sys.stderr)
        sys.exit(2)

    # Entrez requires an email address to identify who is making the request
    Entrez.email = args.email
    if args.api_key:
        Entrez.api_key = args.api_key

    try:
        print(f"Searching NCBI Nucleotide for: {args.term!r}")
        ids = search_nucleotide_ids(args.term, args.max_seqs)
        if not ids:
            print("No nucleotide sequences found for that search term.")
            return

        print(f"Found {len(ids)} record(s). Fetching sequences...")
        records = fetch_sequences(ids)
        if not records:
            print("No sequence data returned by NCBI.")
            return

        print(f"Running BLAST for {len(records)} sequence(s)...\n")
        for index, record in enumerate(records, start=1):
            print(f"[{index}/{len(records)}] {record.id}: submitting BLAST...")
            alignment_count = count_alignments(record, args.blast_db)
            print(f"  {record.id}\talignments: {alignment_count}")

    except HTTPError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()