#!/usr/bin/env python3
"""
Cron entry point for the Railway Cron Job service. Does NOT touch the
filesystem or the Instagram API itself — this service has no access to the
web service's Volume (Railway volumes can't be shared between services), so
it just makes an HTTP call to the web service and lets that process (which
does have the Volume mounted) do the actual work. See
publish_scheduled_posts.py and server.py's /admin/publish-due for what
actually runs.

Configure this service's start command as `python3 trigger_publish.py` and
set WEB_SERVICE_URL to the web service's public Railway domain (e.g.
https://socmedpipeline-working-production-a90a.up.railway.app).
"""

import os
import sys

import requests

WEB_SERVICE_URL = os.environ.get("WEB_SERVICE_URL")


def main():
    if not WEB_SERVICE_URL:
        print("✗ WEB_SERVICE_URL not set on this service — nothing to trigger.")
        sys.exit(1)

    url = f"{WEB_SERVICE_URL.rstrip('/')}/admin/publish-due"
    print(f"POST {url}")
    try:
        response = requests.post(url, timeout=120)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"✗ Trigger failed: {e}")
        sys.exit(1)

    data = response.json()
    print(data.get("output", data))


if __name__ == "__main__":
    main()
