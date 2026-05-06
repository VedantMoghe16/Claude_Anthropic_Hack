"""
Adhikar-Aina | notifier.py

Policy-change notification engine.
When a new scheme is added, finds every citizen who:
  1. Is eligible (rule-based match)
  2. Has a linked Telegram chat_id
  ...and sends them a Telegram message.

CLI:
  python notifier.py --scheme-id SCH-DEMO-001
  python notifier.py --demo          (injects a demo scheme + notifies)
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, TELEGRAM_TOKEN


# ── Telegram sender (direct HTTP, no bot framework needed) ────────────────────

def _send_telegram(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN not set")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=15,
        )
        if r.status_code == 200:
            return True
        print(f"  Telegram send failed [{r.status_code}]: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"  Telegram send error: {e}")
        return False


def _format_notification(citizen: Dict[str, Any], scheme: Dict[str, Any]) -> str:
    name    = citizen.get("name", "Citizen")
    benefit = str(scheme.get("benefit", ""))[:300]
    return (
        f"🔔 <b>New Government Scheme Alert!</b>\n\n"
        f"Namaste <b>{name}</b>!\n\n"
        f"A new scheme has been added that you are eligible for:\n\n"
        f"📋 <b>{scheme['scheme_name']}</b>\n"
        f"🏛 {scheme.get('ministry', 'Government of India')}\n\n"
        f"💰 <b>Benefit:</b> {benefit}\n\n"
        f"<i>Send your Aadhaar number ({citizen.get('aadhar','')[:4]}XXXX"
        f"{citizen.get('aadhar','')[-4:]}) to get your Adhikar Certificate.</i>\n\n"
        f"⚖️ <b>Aapka Adhikar, Aapki Pehchaan</b>"
    )


# ── Eligibility check against a single scheme ────────────────────────────────

def _citizen_eligible(citizen: Dict[str, Any], scheme: Dict[str, Any]) -> bool:
    income = float(citizen.get("annual_income", 0) or 0)
    land   = float(citizen.get("land_acres",    0) or 0)
    occ    = str(citizen.get("occupation_category",
                             citizen.get("occupation", "")) or "").lower().strip()
    cat    = str(citizen.get("caste_category", "GEN") or "GEN").upper().strip()

    min_inc = float(scheme.get("min_income", 0) or 0)
    max_inc = float(scheme.get("max_income", 1e8) or 1e8)
    max_lnd = float(scheme.get("max_land",   1e6) or 1e6)
    s_occ   = str(scheme.get("occupation", "any") or "any").lower().strip()
    s_cat   = str(scheme.get("category",   "ANY") or "ANY").upper().strip()

    if not (min_inc <= income <= max_inc):
        return False
    if land > max_lnd:
        return False
    if s_occ not in ("any", occ):
        return False
    if s_cat not in ("ANY", cat):
        return False
    return True


# ── Core notification function ────────────────────────────────────────────────

def notify_new_scheme(scheme: Dict[str, Any],
                      dry_run: bool = False) -> Dict[str, Any]:
    """
    Find every citizen eligible for `scheme` who has a linked Telegram chat_id
    and send them a notification.

    Returns stats dict: {total_eligible, notified, failed, skipped_no_telegram}
    """
    stats = {"total_eligible": 0, "notified": 0,
             "failed": 0, "skipped_no_telegram": 0}

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        citizens = [dict(r) for r in conn.execute("SELECT * FROM citizens").fetchall()]
        mappings = {
            row["citizen_id"]: row["telegram_chat_id"]
            for row in conn.execute(
                "SELECT citizen_id, telegram_chat_id FROM telegram_user_mapping"
            ).fetchall()
        }

    print(f"\nChecking {len(citizens):,} citizens against: {scheme['scheme_name']}")
    print(f"Telegram-linked citizens: {len(mappings)}")

    for citizen in citizens:
        if not _citizen_eligible(citizen, scheme):
            continue
        stats["total_eligible"] += 1
        chat_id = mappings.get(citizen["citizen_id"])
        if not chat_id:
            stats["skipped_no_telegram"] += 1
            continue

        msg = _format_notification(citizen, scheme)
        print(f"  → Notifying {citizen['name']} (chat_id={chat_id})"
              + (" [DRY RUN]" if dry_run else ""))
        if dry_run:
            stats["notified"] += 1
            continue

        if _send_telegram(chat_id, msg):
            stats["notified"] += 1
            print(f"    ✓ Sent")
        else:
            stats["failed"] += 1
            print(f"    ✗ Failed")

    return stats


# ── Demo scheme (targets OBC entrepreneurs in Karnataka, income < 2.5L) ──────

DEMO_SCHEME = {
    "scheme_id":        "SCH-DEMO-KARN-001",
    "scheme_name":      "Karnataka OBC Women Entrepreneurship Grant",
    "min_income":       0.0,
    "max_income":       250000.0,
    "occupation":       "entrepreneur",
    "max_land":         999999.0,
    "category":         "OBC",
    "benefit":          (
        "One-time grant of Rs 50,000 for women OBC entrepreneurs to expand "
        "micro and small businesses. Includes free mentorship, subsidised GST "
        "registration, and priority access to government procurement tenders."
    ),
    "eligibility_text": (
        "OBC category entrepreneurs in Karnataka with annual income below "
        "Rs 2.5 lakh. Preference for women entrepreneurs and girl-child households."
    ),
    "details":          (
        "Launched under the Karnataka OBC Development Corporation. "
        "Apply at nearest Seva Sindhu portal or District Industry Centre."
    ),
    "scheme_category":  "Women & Child Development,Social welfare & Empowerment",
    "ministry":         "Karnataka State Government — OBC Development Corporation",
    "level":            "State",
    "tags":             "entrepreneur,obc,women,karnataka,grant,startup,self-employment",
}


def add_scheme_to_db(scheme: Dict[str, Any]) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO schemes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            scheme["scheme_id"], scheme["scheme_name"],
            scheme["min_income"], scheme["max_income"],
            scheme["occupation"], scheme["max_land"],
            scheme["category"], scheme["benefit"],
            scheme["eligibility_text"], scheme["details"],
            scheme["scheme_category"], scheme["ministry"],
            scheme["level"], scheme["tags"],
        ))
        conn.commit()
    print(f"Added scheme → {scheme['scheme_name']} ({scheme['scheme_id']})")


def get_scheme_by_id(scheme_id: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM schemes WHERE scheme_id=?", (scheme_id,)
        ).fetchone()
    return dict(row) if row else None


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adhikar — policy notification engine"
    )
    parser.add_argument("--demo",      action="store_true",
                        help="Inject demo Karnataka OBC Entrepreneur scheme + notify")
    parser.add_argument("--scheme-id", type=str,
                        help="Notify for an existing scheme_id already in the DB")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print who would be notified without sending")
    args = parser.parse_args()

    if args.demo:
        print("Injecting demo scheme into database...")
        add_scheme_to_db(DEMO_SCHEME)
        scheme = DEMO_SCHEME
    elif args.scheme_id:
        scheme = get_scheme_by_id(args.scheme_id)
        if not scheme:
            print(f"Scheme '{args.scheme_id}' not found in DB.")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(0)

    stats = notify_new_scheme(scheme, dry_run=args.dry_run)

    print(f"\n── Notification Summary ──────────────────")
    print(f"  Eligible citizens   : {stats['total_eligible']:,}")
    print(f"  Notified via Telegram: {stats['notified']}")
    print(f"  No Telegram linked  : {stats['skipped_no_telegram']}")
    print(f"  Failed to send      : {stats['failed']}")


if __name__ == "__main__":
    main()
