# app/app.py
import os
import json
import uuid
import sys
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

NSJAIL_CMD = os.environ.get("NSJAIL_CMD", "/usr/bin/nsjail")
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)
# If you have a runner wrapper, set RUNNER_PATH; otherwise you can run script directly.
RUNNER_PATH = os.environ.get("RUNNER_PATH", "/app/runner.py")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "nsjail Flask API running"})


@app.route("/execute", methods=["POST"])
def run_code():
    
    data = request.get_json(silent=True) or {}
    code = data.get("scrpit")

    if not code or not isinstance(code, str):
        return jsonify({"error": "Missing or invalid 'scrpit' field"}), 400

    if len(code) > 10000:
        return jsonify({"error": "scrpit too long"}), 400

    # Write user code to a temp file in /tmp
    script_id = str(uuid.uuid4())
    script_path = f"/tmp/user_code_{script_id}.py"

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        return jsonify({"error": f"Failed to write temp script: {e}"}), 500

    # nsjail command – NO cgroup flags, only rlimits (values are in MB!)
    cmd = [
            NSJAIL_CMD,
            "--quiet",
            "--disable_proc",
            "--max_cpus", "1",
            "--time_limit", "5",

            "--rlimit_as", "256",
            "--rlimit_stack", "64",
            "--rlimit_nproc", "32",

            "--chroot", "/",

            # 👇 drop privileges inside the jail
            "--user", "65534",
            "--group", "65534",

            "--",
            PYTHON_BIN,
            RUNNER_PATH,   # or script_path if direct
            script_path,
        ]



    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,  # outer safety timeout
        )
    except subprocess.TimeoutExpired:
        _safe_remove(script_path)
        return jsonify({"error": "Execution timed out"}), 408
    except FileNotFoundError:
        _safe_remove(script_path)
        return jsonify({"error": "nsjail binary not found"}), 500
    except Exception as e:
        _safe_remove(script_path)
        return jsonify({"error": f"Failed to execute nsjail: {e}"}), 500

    _safe_remove(script_path)

    clean_stdout = result.stdout.strip()
    parsed = None

    try:
        parsed = json.loads(clean_stdout)
    except Exception:
        parsed = None
    
    returnValue = parsed.get("result")

    if not isinstance(returnValue, dict):
        return jsonify({"error": " 'scrpit' does return a JSON file"}), 400

    # Build final API response
    if parsed and isinstance(parsed, dict):
        resp = {
            "return": parsed.get("result"),
            "stdout": parsed.get("stdout", "").strip()
        }
    else:
        # Raw fallback (no JSON inside stdout)
        resp = {
            "return": None,
            "stdout": clean_stdout
        }
    status = 200 if result.returncode == 0 else 400
    return jsonify(resp), status


def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
