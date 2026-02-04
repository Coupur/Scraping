import argparse
import re

import pandas as pd
import matplotlib.pyplot as plt


COURSE_NUM_RE = re.compile(r"(\d{3})")


def extract_course_number(row: pd.Series) -> int | None:
    course_display = str(row.get("course_display", "")).strip()
    if not course_display:
        return None
    # Use only the left side of " - " and remove any trailing letters (e.g., 470H -> 470).
    left = course_display.split(" - ", 1)[0]
    match = COURSE_NUM_RE.search(left)
    return int(match.group(1)) if match else None


def level_bucket(course_num: int | None) -> str:
    if course_num is None:
        return "Unknown"
    if 100 <= course_num <= 299:
        return "Intro (100-200)"
    if 300 <= course_num <= 499:
        return "Advanced (300-400)"
    if 500 <= course_num <= 799:
        return "Graduate (500+)"
    return "Unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in",
        dest="input_csv",
        default=r"c:\Users\samut\Desktop\DataSciClub\Scraping\handmade_nau_courses_ai.csv",
        help="Input CSV path",
    )
    ap.add_argument("--out", dest="output_png", default="level_split.png", help="Output PNG path")
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv)
    df["course_num"] = df.apply(extract_course_number, axis=1)
    df["level"] = df["course_num"].apply(level_bucket)

    counts = df["level"].value_counts().reindex(
        ["Intro (100-200)", "Advanced (300-400)", "Graduate (500+)"],
        fill_value=0,
    )

    plt.figure(figsize=(8, 5))
    counts.plot(kind="bar")
    plt.xlabel("Level")
    plt.ylabel("Count")
    plt.title("AI Courses: Intro vs Advanced vs Graduate")
    plt.tight_layout()
    plt.savefig(args.output_png, dpi=150)
    print(f"Saved plot to {args.output_png}")


if __name__ == "__main__":
    main()
