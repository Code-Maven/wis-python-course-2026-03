#!/usr/bin/env python3
"""
Search NCBI Nucleotide for a term, run BLAST for each sequence, then take the
top 3 sequences with the most alignments and look up their PubMed references.

Requires Biopython:
    pip install biopython

Example:
    python ncbi_blast_alignment_count.py "influenza a virus hemagglutinin" --email you@example.com --max-seqs 10
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
            "Search NCBI Nucleotide by term, count BLAST alignments, then report "
            "PubMed references for the top N sequences by alignment count."
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
        default=10,
        help="Maximum number of sequences to fetch from the search results (default: 10)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of top sequences (by alignment count) to look up in PubMed (default: 3)",
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


def fetch_pubmed_references(ncbi_id: str) -> list[dict[str, str]]:
    """Return PubMed articles linked to the given NCBI nucleotide ID.

    Each entry in the returned list is a dict with keys 'title' and 'url'.
    """
    # elink finds cross-database links (nucleotide -> pubmed)
    link_handle = Entrez.elink(dbfrom="nucleotide", db="pubmed", id=ncbi_id)
    link_results = Entrez.read(link_handle)
    link_handle.close()

    pmids: list[str] = []
    for link_set in link_results:
        for db_link in link_set.get("LinkSetDb", []):
            if db_link.get("DbTo") == "pubmed":
                pmids.extend(link["Id"] for link in db_link.get("Link", []))

    if not pmids:
        return []

    # efetch retrieves article metadata in XML format
    fetch_handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="xml", retmode="xml")
    articles = Entrez.read(fetch_handle)
    fetch_handle.close()

    references: list[dict[str, str]] = []
    for article in articles.get("PubmedArticle", []):
        medline = article.get("MedlineCitation", {})
        article_data = medline.get("Article", {})
        title = str(article_data.get("ArticleTitle", "")).strip()
        pmid = str(medline.get("PMID", "")).strip()
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
        references.append({"title": title, "url": url})

    return references


def main() -> None:
    args = parse_args()

    if args.max_seqs <= 0:
        print("--max-seqs must be greater than 0", file=sys.stderr)
        sys.exit(2)

    if args.top_n <= 0:
        print("--top-n must be greater than 0", file=sys.stderr)
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

        # Pair each record with its NCBI ID so we can use elink later
        id_record_pairs = list(zip(ids, records))

        print(f"Running BLAST for {len(id_record_pairs)} sequence(s)...\n")
        results: list[tuple[int, str, SeqIO.SeqRecord]] = []
        for index, (ncbi_id, record) in enumerate(id_record_pairs, start=1):
            print(f"[{index}/{len(id_record_pairs)}] {record.id}: submitting BLAST...")
            alignment_count = count_alignments(record, args.blast_db)
            print(f"  {record.id}\talignments: {alignment_count}")
            results.append((alignment_count, ncbi_id, record))

        # Sort descending by alignment count and take the top args.top_n sequences
        results.sort(key=lambda x: x[0], reverse=True)
        top_results = results[:args.top_n]

        print(f"\n--- Top {args.top_n} sequences by alignment count ---")
        for rank, (alignment_count, ncbi_id, record) in enumerate(top_results, start=1):
            print(f"\n#{rank}  {record.id}  (alignments: {alignment_count})")
            print(f"  Fetching PubMed references for NCBI ID {ncbi_id}...")
            references = fetch_pubmed_references(ncbi_id)
            if references:
                print(f"  Found {len(references)} PubMed reference(s):")
                for ref in references:
                    print(f"    Title: {ref['title']}")
                    print(f"    Link:  {ref['url']}")
            else:
                print("  No PubMed references found.")

    except HTTPError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()