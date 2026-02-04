import argparse
import os
import re

import pandas as pd


TERM_RE = re.compile(r"(\d{4})")


def extract_term(path: str) -> str:
    base = os.path.basename(path)
    match = TERM_RE.search(base)
    return match.group(1) if match else "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", nargs="+", required=True, help="Input CSV files")
    ap.add_argument("--out", default="nau_courses_combined.csv", help="Output CSV path")
    ap.add_argument(
        "--dedup-out",
        default="nau_courses_dedup.csv",
        help="Output CSV path after removing duplicates",
    )
    ap.add_argument(
        "--diff-out",
        default="nau_courses_description_changes.csv",
        help="CSV for courses whose descriptions changed across terms",
    )
    args = ap.parse_args()

    frames = []
    for path in args.inputs:
        df = pd.read_csv(path)
        df["term"] = extract_term(path)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(args.out, index=False)
    print(f"Saved combined file: {args.out} ({len(combined):,} rows)")

    # Normalize description for comparison across terms.
    combined["description_norm"] = (
        combined["description"].fillna("").str.strip().str.replace(r"\s+", " ", regex=True)
    )

    # Identify course_ids with multiple distinct descriptions across terms.
    desc_counts = (
        combined.groupby("course_id")["description_norm"].nunique(dropna=False).reset_index()
    )
    changed_ids = desc_counts[desc_counts["description_norm"] > 1]["course_id"]
    changes = combined[combined["course_id"].isin(changed_ids)].copy()
    changes.to_csv(args.diff_out, index=False)
    print(f"Saved description changes: {args.diff_out} ({len(changes):,} rows)")

    # Remove duplicates across terms (same course_id) after confirming description matches.
    dedup = combined[~combined["course_id"].isin(changed_ids)].copy()
    dedup = dedup.drop(columns=["description_norm"]).drop_duplicates(subset=["course_id"])
    dedup.to_csv(args.dedup_out, index=False)
    print(f"Saved deduped file: {args.dedup_out} ({len(dedup):,} rows)")


if __name__ == "__main__":
    main()
