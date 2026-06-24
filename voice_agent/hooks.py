"""Hooks to integrate editor_agent HTTP service with pipelines.

Functions here call the local `editor_agent` service endpoints when available.
"""

import json
import os
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

EDITOR_AGENT_URL = os.environ.get("EDITOR_AGENT_URL", "http://127.0.0.1:8001")


def _request_post(url: str, payload: dict) -> dict:
    if requests is not None:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json() if resp.status_code == 200 else {}

    parsed = urlparse(url)
    import http.client
    conn = http.client.HTTPConnection(parsed.netloc)
    headers = {"Content-Type": "application/json"}
    conn.request("POST", parsed.path, body=json.dumps(payload).encode(), headers=headers)
    resp = conn.getresponse()
    if resp.status != 200:
        return {}
    return json.loads(resp.read())


def call_editor_edit_and_approve(text: str, job_id: str = None, instructions: str = None) -> dict:
    url = EDITOR_AGENT_URL + "/editor/edit_and_approve"
    payload = {"job_id": job_id, "text": text, "instructions": instructions}
    return _request_post(url, payload)


def call_editor_preview(job_id: str, segment_text: str, voice: str = None):
    url = EDITOR_AGENT_URL + f"/jobs/{job_id}/preview"
    payload = {"segment_text": segment_text, "voice": voice}
    return _request_post(url, payload)


if __name__ == "__main__":
    print(call_editor_edit_and_approve("Teste de edição", job_id="demo123"))
