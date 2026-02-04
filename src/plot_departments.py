import argparse

import pandas as pd
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_csv", default="nau_courses_dedup.csv", help="Input CSV path")
    ap.add_argument("--out", dest="output_png", default="dept_counts.png", help="Output PNG path")
    ap.add_argument("--top", type=int, default=20, help="Top N departments to plot")
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv)
    counts = df["subject"].value_counts().sort_values(ascending=True)
    if args.top and args.top > 0:
        counts = counts.tail(args.top)

    plt.figure(figsize=(10, 8))
    counts.plot(kind="barh")
    plt.xlabel("Count")
    plt.ylabel("Department")
    plt.title(f"Top {len(counts)} Departments by Count (Ascending)")
    plt.tight_layout()
    plt.savefig(args.output_png, dpi=150)
    print(f"Saved plot to {args.output_png}")


if __name__ == "__main__":
    main()
