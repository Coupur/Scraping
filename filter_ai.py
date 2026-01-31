import argparse
import re

import pandas as pd


AI_PATTERN = re.compile(r"\bAI\b|artificial intelligence", flags=re.IGNORECASE)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_csv", default="nau_courses.csv", help="Input CSV path")
    ap.add_argument("--out", dest="output_csv", default="nau_courses_ai.csv", help="Output CSV path")
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv)
    # Handle missing descriptions and match common AI mentions.
    mask = df["description"].fillna("").str.contains(AI_PATTERN, regex=True)
    ai_df = df[mask].copy()
    ai_df.to_csv(args.output_csv, index=False)
    print(f"Saved {len(ai_df):,} AI-related courses to {args.output_csv}")


if __name__ == "__main__":
    main()
