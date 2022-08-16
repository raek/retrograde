from collections import namedtuple
from hashlib import sha256
import json
from pathlib import Path

import appdirs
import fasteners
import gemurl


Settings = namedtuple("Settings", "name, base_url")


def get_orbit_dir(orbit_id, check_exists=True):
    path = Path(appdirs.user_state_dir("retrograde")) / orbit_id
    if check_exists:
        settings_path = path / "settings.json"
        if not settings_path.exists():
            raise Exception(f"Orbit settings file does not exist: {settings_path}")
    return path


def init_settings(orbit_dir, settings):
    path = Path(orbit_dir) / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(settings._asdict(), f, indent=4, sort_keys=True)


def read_settings(orbit_dir):
    path = Path(orbit_dir) / "settings.json"
    with path.open("r", encoding="utf-8") as f:
        return Settings(**json.load(f))


def extend_orbit(orbit, url):
    if url in orbit:
        return orbit
    new_orbit = list(orbit)
    new_orbit.append(url)
    new_orbit.sort(key=_key_fn)
    return new_orbit


def _key_fn(url):
    # Alphabetic order is boring. Let's do someting more interesing.
    return sha256(gemurl.capsule_prefix(url).encode("us-ascii")).digest(), url


def read_orbit(orbit_dir):
    path = Path(orbit_dir) / "members.json"
    with fasteners.InterProcessReaderWriterLock(f"{path}.lock").read_lock():
        return _read_list(path)


def update_url_membership(orbit_dir, url, is_member):
    path = Path(orbit_dir) / "members.json"
    with fasteners.InterProcessReaderWriterLock(f"{path}.lock").write_lock():
        orbit = _read_list(path)
        was_member = url in orbit
        if is_member and not was_member:
            orbit = extend_orbit(orbit, url)
        elif not is_member and was_member:
            orbit.remove(url)
        _write_list(path, orbit)
        return was_member


def append_submission(orbit_dir, url):
    path = Path(orbit_dir) / "submissions.json"
    with fasteners.InterProcessLock(f"{path}.lock"):
        try:
            submissions = _read_list(path)
        except OSError:
            submissions = []
        if url not in submissions:
            submissions.append(url)
            _write_list(path, submissions)


def pop_submission(orbit_dir):
    path = Path(orbit_dir) / "submissions.json"
    with fasteners.InterProcessLock(f"{path}.lock"):
        submissions = _read_list(path)
        if not submissions:
            return None
        submission = submissions.pop(0)
        _write_list(path, submissions)
        return submission


def _read_list(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []


def _write_list(path, list_):
    if list_:
        with path.open("w", encoding="utf-8") as f:
            json.dump(list_, f, indent=4, sort_keys=True)
    else:
        path.unlink(missing_ok=True)
