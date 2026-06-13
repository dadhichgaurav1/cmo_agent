#!/usr/bin/env python3
"""Push a build-in-public post to your StratCMO Action Board as a card.

Your code never leaves your machine — only the post text does. This script sends ONE
HTTP request: the drafted post becomes a `drafted` card on your board, where you review
it and press send. It posts nothing anywhere itself.

Auth + target come from the environment:
  STRATCMO_TOKEN   a CLI token (starts with "scmo_"); mint one in StratCMO settings
  STRATCMO_URL     your StratCMO base URL (default: https://stratcmo.app)
  STRATCMO_SLUG    the company slug the card belongs to (e.g. "acme-com"); optional but
                   recommended — without it the card won't show on a per-company board

Usage:
  python push_card.py --platform x --title "Shipped X" --body "..."
  python push_card.py --platform linkedin --title "..." --body-file post.md
  echo "the post text" | python push_card.py --platform x --title "Shipped X"
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(description="Push a build-in-public post to StratCMO as a card.")
    ap.add_argument("--platform", default="x", choices=["x", "linkedin", "reddit", "hackernews", "indiehackers", "other"])
    ap.add_argument("--title", required=True, help="short card title (for the board face)")
    ap.add_argument("--body", help="the post text; or use --body-file, or pipe via stdin")
    ap.add_argument("--body-file", help="read the post text from this file")
    ap.add_argument("--slug", default=os.environ.get("STRATCMO_SLUG", ""), help="company slug the card belongs to")
    args = ap.parse_args()

    body = args.body
    if args.body_file:
        with open(args.body_file) as f:
            body = f.read()
    if not body and not sys.stdin.isatty():
        body = sys.stdin.read()
    if not body or not body.strip():
        print("error: no post body (use --body, --body-file, or pipe via stdin)", file=sys.stderr)
        return 2

    token = os.environ.get("STRATCMO_TOKEN", "").strip()
    if not token:
        print("error: set STRATCMO_TOKEN (mint a CLI token in StratCMO settings)", file=sys.stderr)
        return 2
    base = os.environ.get("STRATCMO_URL", "https://stratcmo.app").rstrip("/")

    payload = {
        "source": "cli", "platform": args.platform, "kind": "post",
        "title": args.title.strip(), "body": body.strip(),
        "state": "drafted", "company_slug": args.slug.strip(),
    }
    req = urllib.request.Request(
        base + "/api/cards", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        print(f"error: {e.code} {e.read().decode()[:200]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"error: could not reach {base}: {e.reason}", file=sys.stderr)
        return 1

    card = out.get("card") or {}
    where = f"{base}  (Action Board"
    where += f" · {args.slug})" if args.slug else ")"
    print(f"✓ pushed a {args.platform} post as a 'drafted' card to {where}")
    if card.get("id"):
        print(f"  card id: {card['id']}  — review it on your board and press send when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
