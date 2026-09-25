import http.server
import re
import shutil
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_reproduce_helpers(source: str) -> str:
    start = source.index("  const safeURL =")
    end = source.index("  const searchShortcut")
    return source[start:end]


def unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ImageErrorRaceTests(unittest.TestCase):
    def test_stale_webp_error_does_not_clobber_next_stage_image(self):
        if shutil.which("google-chrome") is None:
            self.skipTest("google-chrome is not installed")
        app = (ROOT / "site/assets/app.js").read_text(encoding="utf-8")
        helpers = extract_reproduce_helpers(app)
        html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>race</title></head>
<body>
<div id="ex-image"></div>
<script>
{helpers}
const stage = document.getElementById('ex-image');
reproduce({{id:'NO-SUCH-ID',titulo:'broken',tem_imagem:true,imagem:'not-http'}}, stage);
stage.replaceChildren();
reproduce({{id:'BR-009',titulo:'ok-work',tem_imagem:true,imagem:'https://example.test/ok'}}, stage);
</script>
</body></html>
"""
        webp = ROOT / "site/assets/acervo/BR-009.webp"
        self.assertTrue(webp.is_file())
        port = unused_port()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "assets/acervo").mkdir(parents=True)
            (tmp_path / "assets/acervo/BR-009.webp").write_bytes(webp.read_bytes())
            (tmp_path / "index.html").write_text(html, encoding="utf-8")

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(tmp_path), **kwargs)

                def log_message(self, format, *args):
                    return

            httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
            httpd.allow_reuse_address = True
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                time.sleep(0.2)
                result = subprocess.run(
                    [
                        "timeout", "12",
                        "google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                        "--disable-extensions", "--no-first-run", "--dump-dom",
                        f"http://127.0.0.1:{port}/index.html",
                    ],
                    capture_output=True, text=True, timeout=20, check=False,
                )
            except subprocess.TimeoutExpired:
                self.fail("chrome --dump-dom timed out")
            finally:
                httpd.shutdown()
                httpd.server_close()
        stage = re.search(r'<div id="ex-image">(.*?)</div>', result.stdout, re.S)
        self.assertIsNotNone(stage, result.stdout[:500])
        markup = stage.group(1)
        self.assertIn('alt="ok-work"', markup)
        self.assertIn("BR-009.webp", markup)
        self.assertNotIn("ex-missing", markup)


if __name__ == "__main__":
    unittest.main()
