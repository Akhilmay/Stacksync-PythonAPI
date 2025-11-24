# worker_app.py
import os
import json
import uuid
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

NSJAIL_CMD = os.environ.get("NSJAIL_CMD", "/usr/bin/nsjail")
PYTHON_BIN = os.environ.get("PYTHON_BIN", "python3")
RUNNER_PATH = os.environ.get("RUNNER_PATH", "/app/runner.py")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "nsjail worker healthy"}), 200


@app.route("/run", methods=["POST"])
def run_code():
    data = request.get_json(silent=True) or {}
    code = data.get("code")

    if not code or not isinstance(code, str):
        return jsonify({"ok": False, "error": "Missing or invalid 'code' field", "stdout": ""}), 400

    if len(code) > 10000:
        return jsonify({"ok": False, "error": "Code too long", "stdout": ""}), 400

    # Per-request temp directory for user script
    tmp_dir = tempfile.mkdtemp(prefix="user_code_")
    script_path = os.path.join(tmp_dir, "script.py")

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to write temp script: {e}", "stdout": ""}), 500

    # nsjail command on VM/GKE – here you can safely use more features
    cmd = [
        NSJAIL_CMD,
        "-Mo",
        "--quiet",

        # Example isolation settings (tune as needed)
        "--time_limit", "5",
        "--max_cpus", "1",
        "--rlimit_as", "512",       # MB
        "--rlimit_stack", "64",     # MB
        "--rlimit_nproc", "32",

        # New namespaces (these *do* work on a normal VM/GKE node)
        "--clone_newuser",
        "--clone_newpid",
        "--clone_newuts",
        "--clone_newipc",
        "--clone_newnet",
        "--clone_newns",

        # Map to nobody user inside the jail
        "--user", "65534",
        "--group", "65534",

        # (Optional) chroot – for true FS isolation you’d point this at a
        # prepared minimal rootfs with python + runner available inside.
        # Example placeholder:
        # "--chroot", "/sandbox_root",

        # We pass script_path as argument to runner.py
        "--",
        PYTHON_BIN,
        RUNNER_PATH,
        script_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Execution timed out", "stdout": ""}), 408
    except FileNotFoundError as e:
        return jsonify({"ok": False, "error": f"nsjail or python not found: {e}", "stdout": ""}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to execute nsjail: {e}", "stdout": ""}), 500

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    # runner.py should print JSON; try to parse it
    try:
        payload = json.loads(stdout)
    except Exception:
        # If runner.py crashed before printing JSON, surface stderr
        return jsonify({
            "ok": False,
            "error": "Runner did not return valid JSON",
            "stdout": stdout,
            "stderr": stderr,
        }), 500

    # Just forward runner.py's payload as-is to Cloud Run
    # It already has: ok, result, stdout, (and maybe error)
    return jsonify(payload), 200
