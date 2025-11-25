import sys
import io
import json
import traceback
from types import ModuleType


def run():
    if len(sys.argv) != 2:
        payload = {
            "ok": False,
            "error": "runner.py expects exactly one argument: path to user script",
            "stdout": "",
        }
        print(json.dumps(payload))
        sys.exit(1)

    script_path = sys.argv[1]

    # Prepare a clean global namespace for user code
    user_globals = {
        "__name__": "__main__",
        "__file__": script_path,
        "__package__": None,
    }

    stdout_buffer = io.StringIO()
    real_stdout = sys.stdout

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Capture all stdout from user code
        sys.stdout = stdout_buffer

        # Execute user script
        exec(compile(code, script_path, "exec"), user_globals)

        # Require a callable main()
        if "main" not in user_globals or not callable(user_globals["main"]):
            raise ValueError("Script must define a callable main() function")

        user_main = user_globals["main"]

        # Call user main()
        result = user_main()

        # Validate JSON-serializability
        try:
            json.dumps(result)
        except TypeError as e:
            raise TypeError("Return value of main() must be JSON-serializable") from e

    except Exception as e:
        # Restore stdout before printing our own JSON
        sys.stdout = real_stdout
        stdout_content = stdout_buffer.getvalue()

        error_msg = f"{e.__class__.__name__}: {e}"
        

        payload = {
            "ok": False,
            "error": error_msg,
            "stdout": stdout_content,
        }
        print(json.dumps(payload))
        sys.exit(1)
    else:
        # Success path
        sys.stdout = real_stdout
        stdout_content = stdout_buffer.getvalue()

        payload = {
            "ok": True,
            "result": result,
            "stdout": stdout_content,
        }
        print(json.dumps(payload))
        sys.exit(0)


if __name__ == "__main__":
    run()
# exec_wrapper.py
import importlib.util
import io
import sys
import json
import traceback
from contextlib import redirect_stdout

def load_module_from_path(path, module_name="user_script"):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main_entry(user_script_path):
    try:
        mod = load_module_from_path(user_script_path)
    except Exception:
        tb = traceback.format_exc()
        # print stacktrace to stdout for debugging
        print("ERROR importing user script:", file=sys.stderr)
        print(tb, file=sys.stderr)
        # write result JSON to stderr indicating failure
        out = {"error": "import_failed", "traceback": tb}
        sys.stderr.write("RESULT_JSON:" + json.dumps({"result": None, "error": out}) + "\n")
        sys.exit(1)

    if not hasattr(mod, "main"):
        tb = "user script does not define main()"
        sys.stderr.write("RESULT_JSON:" + json.dumps({"result": None, "error": tb}) + "\n")
        sys.exit(1)

    # capture stdout produced by user's main (so host can receive it separately)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            retval = mod.main()
    except Exception:
        tb = traceback.format_exc()
        # write traceback to stderr and result marker
        sys.stderr.write("RESULT_JSON:" + json.dumps({"result": None, "error": "exception_in_main", "traceback": tb}) + "\n")
        sys.stdout.write(buf.getvalue())
        sys.exit(1)

    # After running main, print captured stdout to stdout (so caller can return it under "stdout")
    captured_stdout = buf.getvalue()
    sys.stdout.write(captured_stdout)

    # Ensure the returned value is JSON-serializable; if not, try to convert or error
    try:
        # Use json.dumps to check
        json.dumps(retval)
    except TypeError:
        # Try convert some common types
        try:
            # convert to string as a fallback
            retval = {"__repr__": repr(retval)}
        except Exception:
            retval = None

    # Write result to stderr as a machine-readable marker
    sys.stderr.write("RESULT_JSON:" + json.dumps({"result": retval}) + "\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: exec_wrapper.py <path_to_user_script>", file=sys.stderr)
        sys.exit(2)
    user_script = sys.argv[1]
    main_entry(user_script)
