"""Start the listening game locally using only the Python standard library."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


def main():
    """Serve the game on localhost and open it in the default browser."""
    root = Path(__file__).resolve().parent / "game"
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    with ThreadingHTTPServer(("127.0.0.1", 8765), handler) as server:
        url = "http://127.0.0.1:8765/web/"
        print(f"Open {url} | Press Ctrl+C to stop.")
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
