# app/app.py
import os
import json
import uuid
import sys
import subprocess
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

WORKER_URL = os.environ.get("WORKER_URL", "http://34.63.44.131:8080/run")
NSJAIL_CMD = os.environ.get("NSJAIL_CMD", "/usr/bin/nsjail")
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)
RUNNER_PATH = os.environ.get("RUNNER_PATH", "/app/runner.py")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "nsjail Flask API running"})


@app.route("/execute", methods=["POST"])
def run_code():
    data = request.get_json(silent=True) or {}
    code = data.get("scrpit")   # keep using the same field name

    if not code or not isinstance(code, str):
        return jsonify({"error": "Missing or invalid 'scrpit' field"}), 400

    if len(code) > 10000:
        return jsonify({"error": "scrpit too long"}), 400

    # Build payload for the worker
    payload = {
        "code": code
    }

    try:
        # Calling the worker (VM/GKE) that actually runs nsjail + runner.py
        resp = requests.post(
            WORKER_URL,
            json=payload,
            timeout=15
        )
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Failed to reach execution worker",
            "details": str(e),
        }), 502

    # Worker responded but with non-200 status
    if resp.status_code != 200:
        return jsonify({
            "error": "Execution worker returned non-200 status",
            "status_code": resp.status_code,
            "body": resp.text,
        }), 502

    # Parse JSON returned by the worker
    try:
        worker_json = resp.json()
    except ValueError:
        return jsonify({
            "error": "Execution worker returned invalid JSON",
            "raw": resp.text,
        }), 502

    # We expect the worker to follow runner.py's contract:
    # { "ok": true/false, "result": ..., "stdout": "...", "error": "..." }
    if not worker_json.get("ok", False):
        return jsonify({
            "error": worker_json.get("error", "Execution failed"),
            "stdout": (worker_json.get("stdout") or "").strip(),
        }), 400

    # Success path: pass back result + stdout in your original shape
    return jsonify({
        "return": worker_json.get("result"),
        "stdout": (worker_json.get("stdout") or "").strip(),
    }), 200
