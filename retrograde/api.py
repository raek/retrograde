import random
from urllib.parse import quote

import gemurl

import retrograde.db as db


def render_dashboard(orbit_dir, url):
    settings = db.read_settings(orbit_dir)
    escaped_url = quote(url, safe="")
    orbit = db.read_orbit(orbit_dir)
    is_member = url in orbit
    check_log = db.read_check_log(orbit_dir, url)
    if check_log is None:
        log_message = "No membership check log found. Submit page for membership check!"
    else:
        log_message = check_log.message
    return f"""# {settings.name} - Page Dashboard
Status: {"IN ORBIT" if is_member else "NOT IN ORBIT"}

=> {url} Visit {url}
=> {settings.base_url}dashboard?{escaped_url} Reload this dashboard
=> {settings.base_url}submit?{escaped_url} Submit page for a membership check
=> {settings.base_url} Back to orbit main page

```Membership Check Log
{log_message}
```

## How to join

For a page to be part of {settings.name}, it needs to be a gemtext page that contains navigation links (next, previous, about). Here are the links made for your URL:

```
Required:
=> {settings.base_url} About {settings.name}
=> {settings.base_url}next?{escaped_url} Next Page
=> {settings.base_url}prev?{escaped_url} Previous Page

Optional:
=> {settings.base_url}random?{escaped_url} Random Page
```

The link text ("Next Page" etc) does not have to be like in the example above, but can be anything.

After you have added the links to the page, visit the "Submit page for membership check" link above.

## How to leave

Remove the navigation links from the page and visit the "Submit page for membership check" link above.

## Retrograde

=> gemini://raek.se/projects/retrograde/ This orbit is powered by Retrograde.
"""


def next_url(orbit_dir, url):
    orbit = db.read_orbit(orbit_dir)
    url = gemurl.normalize_url(url)
    if url not in orbit:
        submit_url(orbit_dir, url)
        orbit = db.extend_orbit(orbit, url)
    index = orbit.index(url)
    new_index = (index + 1) % len(orbit)
    return orbit[new_index]


def prev_url(orbit_dir, url):
    orbit = db.read_orbit(orbit_dir)
    url = gemurl.normalize_url(url)
    if url not in orbit:
        submit_url(orbit_dir, url)
        orbit = db.extend_orbit(orbit, url)
    index = orbit.index(url)
    new_index = (index - 1) % len(orbit)
    return orbit[new_index]


def random_url(orbit_dir, url=None):
    orbit = db.read_orbit(orbit_dir)
    if url is not None:
        url = gemurl.normalize_url(url)
        if url in orbit:
            orbit.remove(url)
        else:
            submit_url(orbit_dir, url)
    if not orbit:
        return None
    return random.choice(orbit)


def list_urls(orbit_dir):
    return db.read_orbit(orbit_dir)


def submit_url(orbit_dir, url):
    url = gemurl.normalize_url(url)
    db.append_submission(orbit_dir, url)
