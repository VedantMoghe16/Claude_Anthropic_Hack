"""
Adhikar-Aina | pipeline.py

Replaces: 06_automation_triggers.py
# DATABRICKS REMOVED: Databricks Jobs API + DeltaTable MERGE replaced with local function calls
# DATABRICKS REMOVED: spark.catalog, spark.table, MERGE INTO → python imports + SQLite

Orchestrates the full local pipeline via CLI:
  --setup                : ingest CSV + generate citizens + build FAISS index
  --aadhar XXXXXXXXXXXX  : match citizen to schemes + generate PDF certificate
  --reset                : delete database and index files (then re-run --setup)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, SCHEME_META_PATH


def cmd_setup() -> None:
    from ingest import run as ingest_run
    from embed_schemes import build_index

    ingest_run()
    print("\nBuilding FAISS semantic index...")
    build_index()
    print("\nSetup complete.")
    print("Next: python pipeline.py --aadhar 999999999999")


def cmd_match(aadhar: str) -> None:
    from match import match_citizen, get_citizen
    from certificate import generate_pdf

    print(f"Looking up Aadhaar: {aadhar[:4]}XXXX{aadhar[-4:]}")
    citizen = get_citizen(aadhar)

    if citizen is None:
        print(f"\nNo citizen found for Aadhaar/ID: {aadhar}")
        print("Tip: run `python pipeline.py --setup` to generate synthetic citizens.")
        sys.exit(1)

    print(f"Found: {citizen['name']} | {citizen['district']} | "
          f"Income: Rs {citizen['annual_income']:,.0f} | {citizen['caste_category']}")

    print("Matching eligible schemes...")
    schemes = match_citizen(aadhar)

    if not schemes:
        print("No eligible schemes found for this citizen profile.")
        sys.exit(0)

    print(f"\nFound {len(schemes)} eligible scheme(s):")
    for i, s in enumerate(schemes, 1):
        print(f"  {i}. {s['scheme_name']}")
        print(f"     Benefit: {str(s['benefit'])[:80]}")

    print("\nGenerating PDF certificate...")
    pdf_path = generate_pdf(citizen, schemes)
    print(f"\nCertificate saved: {pdf_path}")


def cmd_reset() -> None:
    for p in [DB_PATH, SCHEME_META_PATH]:
        if Path(p).exists():
            Path(p).unlink()
            print(f"Deleted: {p}")
    print("Reset complete. Run `python pipeline.py --setup` to rebuild.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adhikar-Aina — Local citizen rights pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python pipeline.py --setup\n"
            "  python pipeline.py --aadhar 999999999999\n"
            "  python pipeline.py --reset"
        )
    )
    parser.add_argument("--setup",  action="store_true",
                        help="Ingest CSV, generate citizens, build FAISS index")
    parser.add_argument("--aadhar", type=str,
                        help="12-digit Aadhaar number to process")
    parser.add_argument("--reset",  action="store_true",
                        help="Delete all generated files and rebuild from scratch")
    args = parser.parse_args()

    if args.reset:
        cmd_reset()
    elif args.setup:
        cmd_setup()
    elif args.aadhar:
        if not args.aadhar.isdigit() or len(args.aadhar) != 12:
            print("Error: Aadhaar must be exactly 12 digits.")
            sys.exit(1)
        cmd_match(args.aadhar)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
