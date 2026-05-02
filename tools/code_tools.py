"""
Python code execution tool for quantitative analysis agents.

The agent writes standard Python (pandas/matplotlib/numpy) as a code string.
This tool runs it in a subprocess, captures stdout, stderr, and any matplotlib
figures (returned as base64-encoded PNG strings).
"""
import base64
import json
import logging
import subprocess
import sys
import textwrap
import tempfile
import os
from typing import Any

logger = logging.getLogger(__name__)

# Injected at the top of every submitted script to configure matplotlib and
# set up the chart-capture mechanism at script exit.
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
    Execute Python code in a sandboxed subprocess and return the results.

    The agent may use pandas, matplotlib, and numpy freely. Any matplotlib
    figures left open at the end of the script are automatically captured and
    returned as base64-encoded PNG strings.

    Args:
        code: Valid Python source code to execute.
        timeout: Maximum wall-clock seconds allowed (default 60).

    Returns:
        A dict with keys:
          - "stdout": captured standard output (chart marker line removed)
          - "stderr": captured standard error
          - "charts": list of base64-encoded PNG strings (one per figure)
          - "error": null on success, or an error message string on failure
    """
    full_code = _PREAMBLE + code + _POSTAMBLE

    # Write to a temp file so the subprocess can be launched cleanly
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
            "charts": [],
            "error": f"Execution timed out after {timeout} seconds.",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": "",
            "charts": [],
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

    return {
        "stdout": "\n".join(clean_lines),
        "stderr": result.stderr,
        "charts": charts,
        "error": error,
    }
