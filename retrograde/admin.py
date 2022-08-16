import argparse
import re
import sys
from urllib.parse import quote

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


def check_url(orbit_dir, url, print_summary=False):
    url = gemurl.normalize_url(url)
    escaped_url = quote(url, safe="")
    settings = db.read_settings(orbit_dir)
    required_links_left = {
        settings.base_url,
        f"{settings.base_url}next?{escaped_url}",
        f"{settings.base_url}prev?{escaped_url}",
    }
    try:
        response = gemcall.request(url)
        while True:
            line = response.readline()
            if not line:
                break
            line = line.decode("utf-8", errors="replace")
            m = re.match(r"=>\s+(?P<url>\S+)", line)
            if not m:
                continue
            link_url = m.group("url")
            # TODO: resolve relative URLs (and normalize them) here
            if link_url in required_links_left:
                required_links_left.remove(link_url)
    except Exception:
        pass
    finally:
        response.discard()
    is_valid = not required_links_left
    was_valid = db.update_url_membership(orbit_dir, url, is_valid)
    if print_summary:
        messages = {
            (False, False): "Remains out of orbit",
            (False, True): "Added to orbit",
            (True, False): "Removed from orbit",
            (True, True): "Remains in orbit",
        }
        print(messages[(was_valid, is_valid)])
        if required_links_left:
            print("Missing links:")
            for link in sorted(required_links_left):
                print(link)
    return was_valid, is_valid
