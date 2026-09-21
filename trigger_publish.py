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
https://<your-service>.up.railway.app), and PIPELINE_API_KEY to the same secret
the web service uses — /admin/publish-due rejects requests without it.
"""

import os
import sys

import requests

WEB_SERVICE_URL = os.environ.get("WEB_SERVICE_URL")
PIPELINE_API_KEY = os.environ.get("PIPELINE_API_KEY")


def main():
    if not WEB_SERVICE_URL:
        print("✗ WEB_SERVICE_URL not set on this service — nothing to trigger.")
        sys.exit(1)
    if not PIPELINE_API_KEY:
        print("✗ PIPELINE_API_KEY not set on this service — the web service will reject the call.")
        sys.exit(1)

    url = f"{WEB_SERVICE_URL.rstrip('/')}/admin/publish-due"
    print(f"POST {url}")
    try:
        response = requests.post(url, headers={"X-API-Key": PIPELINE_API_KEY}, timeout=120)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"✗ Trigger failed: {e}")
        sys.exit(1)

    data = response.json()
    print(data.get("output", data))


if __name__ == "__main__":
    main()
