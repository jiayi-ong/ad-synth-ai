"""
Python code execution tool for quantitative analysis agents.

The agent writes standard Python (pandas/matplotlib/numpy) as a code string.
This tool runs it in a subprocess, captures stdout, stderr, and any matplotlib
figures. Charts are stored in a module-level registry keyed by a UUID so that
large base64 data never reaches the LLM's context window. The generation backend
drains charts by UUID via drain_charts().
"""
import json
import logging
import subprocess
import sys
import textwrap
import tempfile
import threading
import uuid
import os
from typing import Any

logger = logging.getLogger(__name__)

# Registry: uuid → list[base64_png_str]. Thread-safe for concurrent requests.
_chart_registry: dict[str, list[str]] = {}
_chart_registry_lock = threading.Lock()


def drain_charts(charts_id: str) -> list[str]:
    """Remove and return charts for the given UUID. Returns [] if not found."""
    with _chart_registry_lock:
        return _chart_registry.pop(charts_id, [])


_PREAMBLE = textwrap.dedent("""\
    import sys as _sys
    import io as _io
    import json as _json
    import base64 as _b64
    try:
        import matplotlib as _mpl
        _mpl.use("Agg")
        import matplotlib.pyplot as _plt
    except ImportError:
        _plt = None

""")

_POSTAMBLE = textwrap.dedent("""\

    # Capture any open matplotlib figures
    _charts = []
    if _plt is not None:
        for _fig_num in _plt.get_fignums():
            _fig = _plt.figure(_fig_num)
            _buf = _io.BytesIO()
            try:
                _fig.savefig(_buf, format="png", bbox_inches="tight", dpi=100)
                _buf.seek(0)
                _charts.append(_b64.b64encode(_buf.read()).decode())
            except Exception:
                pass
        _plt.close("all")
    # Write chart marker on its own line so it can be parsed out of stdout
    print(f"__CHARTS__:{_json.dumps(_charts)}", flush=True)
""")

_CHART_MARKER = "__CHARTS__:"


def execute_python(code: str, timeout: int = 60) -> dict[str, Any]:
    """
    Execute Python code in a sandboxed subprocess and return results.
    Prints go to "stdout". Any matplotlib figures left open are captured
    automatically — do NOT call plt.close() in your code. The response
    includes "stdout", "stderr", "charts_count" (number of charts captured),
    "_charts_id" (opaque ID used by the pipeline to retrieve chart images),
    and "error" (null on success). Chart images are never returned directly
    to avoid large base64 data in the model context.

    Args:
        code: Valid Python source code to execute.
        timeout: Maximum wall-clock seconds allowed (default 60).
    """
    logger.info("execute_python called: code_len=%d timeout=%d", len(code), timeout)
    full_code = _PREAMBLE + code + _POSTAMBLE

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(full_code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "",
            "charts_count": 0,
            "_charts_id": None,
            "error": f"Execution timed out after {timeout} seconds.",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": "",
            "charts_count": 0,
            "_charts_id": None,
            "error": f"Failed to launch subprocess: {exc}",
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Parse chart marker out of stdout
    stdout_lines = result.stdout.splitlines()
    clean_lines: list[str] = []
    charts: list[str] = []
    for line in stdout_lines:
        if line.startswith(_CHART_MARKER):
            try:
                charts = json.loads(line[len(_CHART_MARKER):])
            except json.JSONDecodeError:
                pass
        else:
            clean_lines.append(line)

    error: str | None = None
    if result.returncode != 0:
        error = result.stderr.strip() or f"Exited with code {result.returncode}"

    # Store charts in registry so the pipeline can retrieve them without
    # passing large base64 strings back to the LLM.
    charts_id: str | None = None
    if charts:
        charts_id = str(uuid.uuid4())
        with _chart_registry_lock:
            _chart_registry[charts_id] = charts

    logger.info(
        "execute_python done: stdout_len=%d stderr_len=%d charts=%d error=%r",
        len("\n".join(clean_lines)), len(result.stderr), len(charts), error,
    )
    return {
        "stdout": "\n".join(clean_lines),
        "stderr": result.stderr,
        "charts_count": len(charts),
        "_charts_id": charts_id,
        "error": error,
    }
