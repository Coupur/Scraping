import argparse
import re

import pandas as pd


# Fuzzy-ish keyword patterns (include misspellings and variants to avoid misses).
STRICT_PATTERNS = [
    r"\bai\b",
    r"ai-",
    r"\bartificial intelligence\b",
    r"\bartificial intelligent\b",
    r"\bgpt\b",
    r"\bchatgpt\b",
    r"\bllm\b",
    r"\bmachine\s+learning\b",
    r"\bgenerative\b",
    r"\bgenarative\b",
]
# Broad terms that can add many non-AI courses (kept for recall).
BROAD_ONLY_PATTERNS = [
    r"\bintelligence\b",
    r"\bagent\b",
    r"\bagentic\b",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_csv", default="nau_courses.csv", help="Input CSV path")
    ap.add_argument("--out", dest="output_csv", default="nau_courses_ai.csv", help="Output CSV path")
    ap.add_argument(
        "--mode",
        choices=["broad", "strict"],
        default="broad",
        help="broad includes intelligence/ethics/agent terms; strict is AI-specific only",
    )
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv)
    patterns = STRICT_PATTERNS + (BROAD_ONLY_PATTERNS if args.mode == "broad" else [])
    ai_pattern = re.compile("|".join(patterns), flags=re.IGNORECASE)
    # Handle missing descriptions and match common AI mentions.
    mask = df["description"].fillna("").str.contains(ai_pattern, regex=True)
    ai_df = df[mask].copy()
    ai_df.to_csv(args.output_csv, index=False)
    print(f"Saved {len(ai_df):,} AI-related courses to {args.output_csv}")


if __name__ == "__main__":
    main()
