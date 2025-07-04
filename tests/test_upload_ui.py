import subprocess
from pathlib import Path


def test_upload_ui_event_listener():
    """Run the UI event listener with jsdom available."""
    # Only install dependencies if they are missing. Using ``npm ci`` ensures
    # a clean, reproducible install when ``node_modules`` is not present.
    if not Path("node_modules").exists():
        subprocess.run(["npm", "ci"], check=True)

    result = subprocess.run([
        "node",
        "tests/ui_event_listener.js",
    ], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "ok"
