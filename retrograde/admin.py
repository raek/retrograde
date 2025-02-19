import argparse
from datetime import datetime, timezone
import re
import sys
from urllib.parse import quote
import traceback

import gemcall
import gemurl

import retrograde.db as db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("orbit_id", help="Identifier for orbit (server-internal)")
    subparsers = parser.add_subparsers(title="subcommands", dest="command")
    subparsers.add_parser("dir", help="Print orbit directory")
    init_parser = subparsers.add_parser("init", help="Create a new orbit")
    init_parser.add_argument("--name", required=True,
                             help="Name of orbit for displaying to visitors.")
    init_parser.add_argument("--base-url", required=True,
                             help=("Base URL for orbit link (such as gemini://example.com/orbits/demo/). " +
                                   "Same as 'next' URL up to the 'next' part."))
    subparsers.add_parser("list", help="List URLs in orbit")
    check_parser = subparsers.add_parser("check", help="Check given URL for orbit links and update its membership")
    check_parser.add_argument("url", help="Page URL for orbit candidate")
    check_log_parser = subparsers.add_parser("check-log", help="Displays the membership check log for the given URL")
    check_log_parser.add_argument("url", help="Page URL for orbit candidate")
    subparsers.add_parser("check-submissions", help="Check submitted URLs")
    args = parser.parse_args()
    if args.command == "dir":
        print(db.get_orbit_dir(args.orbit_id, check_exists=False))
    elif args.command == "init":
        settings = db.Settings(args.name, gemurl.normalize_url(args.base_url))
        db.init_settings(db.get_orbit_dir(args.orbit_id, check_exists=False), settings)
    elif args.command == "list":
        for url in db.read_orbit(db.get_orbit_dir(args.orbit_id)):
            print(url)
    elif args.command == "check":
        check_url(db.get_orbit_dir(args.orbit_id), args.url, print_summary=True)
    elif args.command == "check-log":
        check_log = db.read_check_log(db.get_orbit_dir(args.orbit_id), args.url)
        if check_log is None:
            print("No check log found.")
        else:
            print(check_log.message, end=None)
    elif args.command == "check-submissions":
        orbit_dir = db.get_orbit_dir(args.orbit_id)
        while True:
            url = db.pop_submission(orbit_dir)
            if url is None:
                break
            print("Checking URL: " + url)
            check_url(orbit_dir, url, print_summary=True)
    elif args.command is None:
        print("No subcommand given")
        sys.exit(1)


_VERDICTS = {
    (False, False): "Remains out of orbit",
    (False, True): "Added to orbit",
    (True, False): "Removed from orbit",
    (True, True): "Remains in orbit",
}


def check_url(orbit_dir, url, print_summary=False):
    dt = datetime.now(timezone.utc)
    timestamp = int(dt.timestamp())
    url = gemurl.normalize_url(url)
    escaped_url = quote(url, safe="")
    settings = db.read_settings(orbit_dir)
    required_links = {
        settings.base_url,
        f"{settings.base_url}next?{escaped_url}",
        f"{settings.base_url}prev?{escaped_url}",
    }
    optional_links = {
        f"{settings.base_url}random?{escaped_url}",
    }
    remaining_required_links = set(required_links)
    remaining_optional_links = set(optional_links)
    found_links = []
    response = None
    try:
        response = gemcall.request(url)
        while True:
            line = response.readline()
            if not line:
                break
            line = line.decode("utf-8", errors="replace")
            m = re.match(r"=>\s?(?P<url>\S+)", line)
            if not m:
                continue
            link_url = m.group("url")
            found_links.append(link_url)
            # TODO: resolve relative URLs (and normalize them) here
            if link_url in remaining_required_links:
                remaining_required_links.remove(link_url)
            if link_url in remaining_optional_links:
                remaining_optional_links.remove(link_url)
    except Exception:
        print(traceback.format_exc())
    finally:
        if response:
            response.discard()
    is_valid = not remaining_required_links
    was_valid = db.update_url_membership(orbit_dir, url, is_valid)
    verdict = _VERDICTS[(was_valid, is_valid)]
    message = f"Timestamp: {dt}\n"
    message += f"Result: {verdict}\n\n"
    message += "Required navigation links:\n"
    for required_link in sorted(required_links):
        if required_link in remaining_required_links:
            message += f"* [MISSING] {required_link}\n"
        else:
            message += f"* [FOUND]   {required_link}\n"
    message += "\n"
    message += "Optional navigation links:\n"
    for optional_link in sorted(optional_links):
        if optional_link in remaining_optional_links:
            message += f"* [MISSING] {optional_link}\n"
        else:
            message += f"* [FOUND]   {optional_link}\n"
    message += "\n"
    if remaining_required_links:
        message += "Other links found on page:\n"
        for found_link in found_links:
            if found_link not in required_links and found_link not in optional_links:
                message += f"* {found_link}\n"
        message += "\n"
    check_log = db.CheckLog(timestamp, is_valid, was_valid, message)
    db.write_check_log(orbit_dir, url, check_log)
    if print_summary:
        print(message, end=None)
    return was_valid, is_valid
