import gemurl
from jetforce import Response, Status

import retrograde.api as api
from retrograde.db import get_orbit_dir, read_settings, angle


def install_orbit_routes(app, orbit_id, mount_prefix):
    orbit_dir = get_orbit_dir(orbit_id)

    @app.route(mount_prefix + "/dashboard")
    def dashboard(request):
        url = request.query
        if not url:
            return Response(Status.INPUT, "Page URL")
        if not url.startswith("gemini://"):
            url = "gemini://" + url
        url = gemurl.normalize_url(url)
        return Response(Status.SUCCESS, "text/gemini", api.render_dashboard(orbit_dir, url))

    @app.route(mount_prefix + "/next")
    def next_page(request):
        if not request.query:
            return Response(Status.INPUT, "Page URL")
        new_url = api.next_url(orbit_dir, request.query)
        return Response(Status.REDIRECT_TEMPORARY, new_url)

    @app.route(mount_prefix + "/prev")
    def prev_page(request):
        if not request.query:
            return Response(Status.INPUT, "Page URL")
        new_url = api.prev_url(orbit_dir, request.query)
        return Response(Status.REDIRECT_TEMPORARY, new_url)

    @app.route(mount_prefix + "/random")
    def random_page(request):
        url = request.query if request.query != "" else None
        new_url = api.random_url(orbit_dir, url)
        if new_url is None:
            return Response(Status.TEMPORARY_FAILURE, "No (other) URLs in orbit!")
        else:
            return Response(Status.REDIRECT_TEMPORARY, new_url)

    @app.route(mount_prefix + "/list")
    def list_pages(request):
        settings = read_settings(orbit_dir)
        urls = api.list_urls(orbit_dir)
        body = f"# {settings.name}\n"
        body += "\n"
        for url in urls:
            body += f"=> {url} {angle(url):3}° – {url}\n"
        return Response(Status.SUCCESS, "text/gemini", body)

    @app.route(mount_prefix + "/submit")
    def submit_page(request):
        if not request.query:
            return Response(Status.INPUT, "Page URL")
        api.submit_url(orbit_dir, request.query)
        return Response(Status.SUCCESS, "text/gemini", "The URL will be checked in a few minutes.")
