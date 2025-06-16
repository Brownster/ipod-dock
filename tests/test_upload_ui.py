import subprocess


def test_upload_ui_event_listener():
    # ensure jsdom installed
    subprocess.run(["npm", "install"], check=True)
    result = subprocess.run(["node", "tests/ui_event_listener.js"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "ok"
