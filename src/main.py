import argparse
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs
import json

import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://catalog.nau.edu"
RESULTS_URL = f"{BASE}/Courses/results"
LOG_PATH = r"c:\Users\samut\Desktop\DataSciClub\Scraping\.cursor\debug.log"
SESSION_ID = "debug-session"


def log_event(run_id: str, hypothesis_id: str, location: str, message: str, data: dict | None = None):
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def get_session():
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "NAU-course-catalog-research-scraper/1.0 (contact: your_email@domain.edu)",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


def parse_course_id(href: str) -> str | None:
    try:
        qs = parse_qs(urlparse(href).query)
        return qs.get("courseId", [None])[0]
    except Exception:
        return None


def extract_description_near_link(a_tag) -> str:
    """
    The results pages usually look like:
      <a ...>CS 105 - ...</a>
      This course introduces ...
    We'll take the first meaningful text after the link in the same container.
    """
    # If the link is inside a <dt>, the description is usually in the next <dd>.
    dt = a_tag.find_parent("dt")
    if dt:
        dd = dt.find_next_sibling("dd")
        if dd:
            text = clean_ws(dd.get_text(" ", strip=True))
            if text:
                if "Description:" in text:
                    text = text.split("Description:", 1)[1]
                for stop in (
                    "Units:",
                    "Sections offered:",
                    "Section(s) offered:",
                    "Prerequisite:",
                    "Prerequisites:",
                    "Corequisite:",
                    "Corequisites:",
                ):
                    if stop in text:
                        text = text.split(stop, 1)[0]
                return clean_ws(text)

    # Try next siblings first
    for node in a_tag.next_siblings:
        # stop if we hit another course link
        if getattr(node, "name", None) == "a":
            break

        txt = ""
        if isinstance(node, str):
            txt = node
        else:
            txt = node.get_text(" ", strip=True) if hasattr(node, "get_text") else ""

        txt = clean_ws(txt)
        if txt:
            return txt

    # Fallback: parent text minus the link text
    parent = a_tag.parent
    if parent:
        full = clean_ws(parent.get_text(" ", strip=True))
        link_txt = clean_ws(a_tag.get_text(" ", strip=True))
        if full.startswith(link_txt):
            return clean_ws(full[len(link_txt) :])
    return ""


def scrape_subject(session: requests.Session, subject: str, term: str | None, delay_s: float):
    # region agent log
    log_event(
        "run2",
        "H4",
        "main.py:scrape_subject:entry",
        "scrape_subject entry",
        {"subject": subject, "term": term, "delay_s": delay_s},
    )
    # endregion
    params = {"subject": subject}
    # Term isn't required for the endpoint to work, but we allow it if you want to try pinning.
    if term:
        params["term"] = term

    r = session.get(RESULTS_URL, params=params, timeout=30)
    r.raise_for_status()

    # region agent log
    log_event(
        "run2",
        "H4",
        "main.py:scrape_subject:response",
        "results response",
        {"status_code": r.status_code, "text_len": len(r.text)},
    )
    # endregion
    soup = BeautifulSoup(r.text, "html.parser")

    rows = []
    # Links to courses look like course?courseId=XXXXX&term=YYYY (relative to /Courses/)
    # region agent log
    link_nodes = soup.select('a[href*="courseId="]')
    log_event(
        "run2",
        "H2",
        "main.py:scrape_subject:links",
        "found course links",
        {"link_count": len(link_nodes)},
    )
    # endregion
    empty_desc_samples = 0
    for a in soup.select('a[href*="courseId="]'):
        href = a.get("href", "")
        url = urljoin(r.url, href)
        course_id = parse_course_id(url)
        title_line = clean_ws(a.get_text(" ", strip=True))
        desc = extract_description_near_link(a)

        if not desc and empty_desc_samples < 3:
            # region agent log
            sibling_texts = []
            for node in list(a.next_siblings)[:5]:
                if isinstance(node, str):
                    txt = node
                else:
                    txt = node.get_text(" ", strip=True) if hasattr(node, "get_text") else ""
                txt = clean_ws(txt)
                if txt:
                    sibling_texts.append(txt[:120])
            parent = a.parent
            log_event(
                "run2",
                "H1",
                "main.py:scrape_subject:empty_desc_sample",
                "empty description sample",
                {
                    "href": href,
                    "title_line": title_line,
                    "parent_tag": getattr(parent, "name", None),
                    "parent_class": " ".join(parent.get("class", [])) if parent else "",
                    "sibling_texts": sibling_texts,
                },
            )
            # endregion
            empty_desc_samples += 1

        if not course_id:
            continue

        rows.append(
            {
                "subject": subject,
                "course_id": course_id,
                "course_display": title_line,   # e.g. "CS 105 - Computing Tools I"
                "description": desc,
                "course_url": url,
            }
        )

    time.sleep(delay_s)
    # region agent log
    log_event(
        "run2",
        "H4",
        "main.py:scrape_subject:exit",
        "scrape_subject exit",
        {"subject": subject, "rows": len(rows)},
    )
    # endregion
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefixes", required=True, help="Path to prefixes.txt (one subject code per line)")
    ap.add_argument("--term", default=None, help="Optional term code (e.g., 1261). Results works without it.")
    ap.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    ap.add_argument("--out", default="nau_courses.csv", help="Output CSV path")
    args = ap.parse_args()

    # region agent log
    log_event(
        "run2",
        "H3",
        "main.py:main:args",
        "parsed args",
        {"prefixes": args.prefixes, "term": args.term, "delay": args.delay, "out": args.out},
    )
    # endregion
    with open(args.prefixes, "r", encoding="utf-8") as f:
        subjects = [line.strip().upper() for line in f if line.strip()]

    # region agent log
    log_event(
        "run2",
        "H3",
        "main.py:main:subjects",
        "loaded subjects",
        {"subject_count": len(subjects)},
    )
    # endregion
    session = get_session()

    all_rows = []
    for subj in tqdm(subjects, desc="Scraping subjects"):
        try:
            all_rows.extend(scrape_subject(session, subj, args.term, args.delay))
        except requests.HTTPError as e:
            print(f"[HTTP ERROR] {subj}: {e}")
        except Exception as e:
            print(f"[ERROR] {subj}: {e}")

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["course_id"])
    if args.term:
        out_path = f"{args.term}_{args.out}"
    else:
        out_path = args.out
    print(f"Saving to {out_path}")
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df):,} courses to {out_path}")


if __name__ == "__main__":
    main()
