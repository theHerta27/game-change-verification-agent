import json
from http.client import HTTPConnection
from threading import Thread

from agent_service.server import AgentServiceHandler, ThreadingHTTPServer


def test_agent_service_review_endpoint():
    server = ThreadingHTTPServer(("127.0.0.1", 0), AgentServiceHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        payload = {
            "diff": "diff --git a/app/client.py b/app/client.py\n--- a/app/client.py\n+++ b/app/client.py\n@@ -1,2 +1,3 @@\n import requests\n+response = requests.get(url)\n",
            "language": "python",
            "mode": "mock",
            "workflow": "dual_agent",
        }
        conn.request("POST", "/agent/review", json.dumps(payload), {"Content-Type": "application/json"})
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    assert response.status == 200
    assert len(body["findings"]) == 1
    assert body["agent_runs"][0]["agent_name"] == "review_agent"
    assert body["agent_runs"][1]["agent_name"] == "test_agent"
