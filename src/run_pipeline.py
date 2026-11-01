"""One-command pipeline: optionally fetch full dataset, ETL, and reporting."""
import argparse
from pathlib import Path
from etl import SAMPLE, FULL, DATABASE, REPORTS, run
from build_reports import build
from download_data import main as download_full

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download full UCI dataset before running")
    parser.add_argument("--sample", action="store_true", help="Use the small included real sample")
    args = parser.parse_args()
    if args.download:
        download_full()
    source = SAMPLE if args.sample else (FULL if FULL.exists() else SAMPLE)
    print(f"Using source: {source.name}")
    run(source, DATABASE, REPORTS / "pipeline_metrics.json")
    build()
