#!/usr/bin/env python3
"""
Search NCBI Nucleotide for a term, then run BLAST for each sequence and
report how many alignments were found.

Example:
    python ncbi_blast_alignment_count.py "influenza a virus hemagglutinin" --max-seqs 3
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"


@dataclass
class SequenceInfo:
    accession: str
    sequence: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search NCBI Nucleotide by term and count BLAST alignments for each result."
        )
    )
    parser.add_argument("term", help="Search term for the NCBI nucleotide database")
    parser.add_argument(
        "--max-seqs",
        type=int,
        default=3,
        help="Maximum number of sequences to fetch from the search results (default: 3)",
    )
    parser.add_argument(
        "--email",
        default="",
        help="Contact email sent to NCBI (recommended)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional NCBI API key for E-utilities requests",
    )
    parser.add_argument(
        "--blast-db",
        default="nt",
        help="BLAST database to search against (default: nt)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=10.0,
        help="Seconds between BLAST status checks (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum seconds to wait for each BLAST job (default: 300)",
    )
    return parser.parse_args()


def http_get(url: str, timeout: int = 60) -> str:
    request = Request(url, headers={"User-Agent": "wis-python-course-example/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def http_post(url: str, payload: dict[str, str], timeout: int = 60) -> str:
    encoded = urlencode(payload).encode("utf-8")
    request = Request(
        url,
        data=encoded,
        headers={
            "User-Agent": "wis-python-course-example/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def search_nucleotide_ids(term: str, max_seqs: int, email: str, api_key: str) -> list[str]:
    params = {
        "db": "nucleotide",
        "term": term,
        "retmode": "xml",
        "retmax": str(max_seqs),
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key

    url = f"{EUTILS_BASE}/esearch.fcgi?{urlencode(params)}"
    xml_text = http_get(url)
    root = ET.fromstring(xml_text)

    ids: list[str] = []
    for elem in root.findall(".//IdList/Id"):
        if elem.text:
            ids.append(elem.text.strip())

    return ids


def fetch_sequences(ids: Iterable[str], email: str, api_key: str) -> list[SequenceInfo]:
    id_list = list(ids)
    if not id_list:
        return []

    params = {
        "db": "nucleotide",
        "id": ",".join(id_list),
        "rettype": "fasta",
        "retmode": "text",
    }
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key

    url = f"{EUTILS_BASE}/efetch.fcgi?{urlencode(params)}"
    fasta_text = http_get(url)
    return parse_fasta(fasta_text)


def parse_fasta(fasta_text: str) -> list[SequenceInfo]:
    records: list[SequenceInfo] = []
    header = ""
    seq_parts: list[str] = []

    for line in fasta_text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith(">"):
            if header and seq_parts:
                records.append(SequenceInfo(accession=extract_accession(header), sequence="".join(seq_parts)))
            header = line[1:]
            seq_parts = []
        else:
            seq_parts.append(line)

    if header and seq_parts:
        records.append(SequenceInfo(accession=extract_accession(header), sequence="".join(seq_parts)))

    return records


def extract_accession(header: str) -> str:
    # Typical header starts with: "accession description..."
    first_field = header.split(" ", 1)[0]
    return first_field.strip() or "unknown_accession"


def submit_blast(sequence: str, database: str) -> tuple[str, int]:
    payload = {
        "CMD": "Put",
        "PROGRAM": "blastn",
        "DATABASE": database,
        "QUERY": sequence,
    }
    response_text = http_post(BLAST_URL, payload, timeout=120)

    rid_match = re.search(r"RID\s*=\s*([A-Z0-9-]+)", response_text)
    rtoe_match = re.search(r"RTOE\s*=\s*(\d+)", response_text)
    if not rid_match:
        raise RuntimeError("BLAST submission did not return RID.")

    rid = rid_match.group(1)
    rtoe = int(rtoe_match.group(1)) if rtoe_match else 15
    return rid, rtoe


def check_blast_status(rid: str) -> tuple[str, bool]:
    params = {
        "CMD": "Get",
        "RID": rid,
        "FORMAT_OBJECT": "SearchInfo",
    }
    url = f"{BLAST_URL}?{urlencode(params)}"
    response_text = http_get(url, timeout=60)

    status_match = re.search(r"Status=(\w+)", response_text)
    hits_match = re.search(r"ThereAreHits=(yes|no)", response_text)

    if not status_match:
        raise RuntimeError(f"Could not read BLAST status for RID={rid}")

    status = status_match.group(1).upper()
    has_hits = hits_match.group(1).lower() == "yes" if hits_match else False
    return status, has_hits


def fetch_blast_xml(rid: str) -> str:
    params = {
        "CMD": "Get",
        "RID": rid,
        "FORMAT_TYPE": "XML",
    }
    url = f"{BLAST_URL}?{urlencode(params)}"
    return http_get(url, timeout=120)


def count_alignments_from_xml(xml_text: str) -> int:
    root = ET.fromstring(xml_text)

    # Legacy BLAST XML format
    hits = root.findall(".//Iteration_hits/Hit")
    if hits:
        return len(hits)

    # Fallback for XML2-like shape
    hits = root.findall(".//hits/Hit")
    if hits:
        return len(hits)

    return 0


def count_alignments_for_sequence(
    sequence: str,
    blast_db: str,
    poll_interval: float,
    timeout_seconds: int,
) -> int:
    rid, rtoe = submit_blast(sequence, blast_db)

    # NCBI recommends waiting RTOE seconds before first status check.
    time.sleep(max(float(rtoe), 1.0))
    start = time.time()

    while True:
        status, has_hits = check_blast_status(rid)

        if status == "READY":
            if not has_hits:
                return 0
            xml_text = fetch_blast_xml(rid)
            return count_alignments_from_xml(xml_text)

        if status in {"FAILED", "UNKNOWN"}:
            raise RuntimeError(f"BLAST failed for RID={rid} with status={status}")

        elapsed = time.time() - start
        if elapsed > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for BLAST RID={rid}")

        time.sleep(max(poll_interval, 1.0))


def main() -> None:
    args = parse_args()

    if args.max_seqs <= 0:
        print("--max-seqs must be greater than 0", file=sys.stderr)
        sys.exit(2)

    try:
        ids = search_nucleotide_ids(args.term, args.max_seqs, args.email, args.api_key)
        if not ids:
            print("No nucleotide sequences found for that search term.")
            return

        sequences = fetch_sequences(ids, args.email, args.api_key)
        if not sequences:
            print("No sequence data returned by NCBI.")
            return

        print(f"Found {len(sequences)} sequence(s). Running BLAST now...")

        for index, record in enumerate(sequences, start=1):
            print(f"[{index}/{len(sequences)}] {record.accession}: submitting BLAST...")
            alignment_count = count_alignments_for_sequence(
                sequence=record.sequence,
                blast_db=args.blast_db,
                poll_interval=args.poll_interval,
                timeout_seconds=args.timeout,
            )
            print(f"{record.accession}\talignments={alignment_count}")

    except (HTTPError, URLError) as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as exc:
        print(f"Could not parse XML response: {exc}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, TimeoutError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()