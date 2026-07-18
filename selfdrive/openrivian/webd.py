#!/usr/bin/env python3
import os
import re
import http.server
import socketserver
import logging
import threading
import urllib.request

PORT = 8081

ROUTE_CACHE = []
ROUTE_CACHE_LOCK = threading.Lock()

ROUTES_PATH = "/data/media/0/realdata/"

# ---------------------------------------------------------------------------
# Map tile proxy + disk cache.
# The dashboard requests /tiles/{z}/{x}/{y}.png from THIS server; we fetch the
# tile from OpenStreetMap once (proper identifying User-Agent, per the OSM tile
# usage policy), persist it, and serve from disk forever after. Wins: the in-car
# screen only ever talks to the comma; every client shares one cache; regular
# routes become offline-capable after the first drive.
# ---------------------------------------------------------------------------
TILE_UPSTREAM = "https://tile.openstreetmap.org"
TILE_USER_AGENT = "OpenRivian-Dashboard/1.0 (personal vehicle project; github.com/adwilson254/openpilot)"
TILE_CACHE_DIR = os.environ.get("ORV_TILE_CACHE", "/data/openrivian/tiles")
TILE_ZOOM_MIN, TILE_ZOOM_MAX = 3, 19
_TILE_RE = re.compile(r"^/tiles/(\d{1,2})/(\d{1,7})/(\d{1,7})\.png$")


def parse_tile_path(path):
    """Validate /tiles/{z}/{x}/{y}.png -> (z, x, y) ints, or None if invalid.
    The regex admits digits only (no traversal), and bounds are checked so a
    hostile path can never escape the cache directory or hit upstream junk."""
    m = _TILE_RE.match(path)
    if not m:
        return None
    z, x, y = (int(g) for g in m.groups())
    if not (TILE_ZOOM_MIN <= z <= TILE_ZOOM_MAX):
        return None
    n = 2 ** z
    if not (0 <= x < n and 0 <= y < n):
        return None
    return z, x, y


def tile_cache_path(z, x, y, cache_dir=None):
    return os.path.join(cache_dir or TILE_CACHE_DIR, str(z), str(x), f"{y}.png")


def fetch_tile(z, x, y, cache_dir=None, opener=None):
    """Return tile PNG bytes from cache or upstream; None when unavailable.
    Never raises: an offline truck must degrade to 'no tile', not a dead daemon."""
    cpath = tile_cache_path(z, x, y, cache_dir)
    try:
        with open(cpath, "rb") as f:
            return f.read()
    except OSError:
        pass
    try:
        req = urllib.request.Request(
            f"{TILE_UPSTREAM}/{z}/{x}/{y}.png", headers={"User-Agent": TILE_USER_AGENT})
        open_fn = opener or urllib.request.urlopen
        with open_fn(req, timeout=10) as resp:
            data = resp.read()
        if not data:
            return None
        try:
            os.makedirs(os.path.dirname(cpath), exist_ok=True)
            tmp = f"{cpath}.tmp.{os.getpid()}.{threading.get_ident()}"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, cpath)  # atomic: concurrent readers never see partial files
        except OSError as e:
            logging.debug(f"tile cache write failed ({cpath}): {e}")
        return data
    except Exception as e:
        logging.debug(f"tile fetch failed {z}/{x}/{y}: {e}")
        return None

# Mock data used when the realdata directory is unavailable (e.g. local dev).
MOCK_ROUTES = [
    {"id": "2023-10-25--14-30-00", "date": "2023-10-25", "size_mb": 450},
    {"id": "2023-10-24--09-15-00", "date": "2023-10-24", "size_mb": 1200},
    {"id": "2023-10-20--18-45-00", "date": "2023-10-20", "size_mb": 310},
]

def scan_routes(routes_path=ROUTES_PATH, io_yield=0.01):
    # Pure-ish helper (no globals/threads) so the route listing is unit-testable.
    # Returns mock data when the realdata directory doesn't exist.
    if not os.path.exists(routes_path):
        return list(MOCK_ROUTES)

    routes = []
    for d in os.listdir(routes_path):
        full = os.path.join(routes_path, d)
        if os.path.isdir(full):
            total_size = 0
            for dirpath, _, filenames in os.walk(full):
                for f in filenames:
                    total_size += os.path.getsize(os.path.join(dirpath, f))
                if io_yield:
                    import time
                    time.sleep(io_yield)  # Yield I/O gracefully
            routes.append({
                "id": d,
                "date": d.split('--')[0] if '--' in d else d,
                "size_mb": total_size // (1024 * 1024),
            })
    return routes

def bg_cache_updater():
    import time
    while True:
        try:
            new_routes = scan_routes()
            with ROUTE_CACHE_LOCK:
                global ROUTE_CACHE
                ROUTE_CACHE = new_routes
        except Exception as e:
            logging.error(f"Error reading routes in bg thread: {e}")

        time.sleep(30) # Only scan the disk every 30 seconds

def main():
    try:
        os.nice(19)
    except Exception as e:
        logging.warning(f"Failed to set nice value: {e}")

    logging.basicConfig(level=logging.INFO)
    
    # Start the background cache updater thread
    threading.Thread(target=bg_cache_updater, daemon=True).start()
    
    # Path to the compiled React app
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard/dist")
    
    if not os.path.exists(web_dir):
        logging.error(f"[-] Web directory not found at {web_dir}. Please run 'npm run build' inside the dashboard directory first.")
        return
        
    os.chdir(web_dir)
    
    # Simple HTTP request handler
    class SPAHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()

        def do_OPTIONS(self):
            self.send_response(200, "ok")
            self.end_headers()

        def do_POST(self):
            self.send_response(404)
            self.end_headers()

        def do_GET(self):
            if self.path == '/routes':
                import json
                with ROUTE_CACHE_LOCK:
                    routes = ROUTE_CACHE.copy()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(routes).encode('utf-8'))
                return

            if self.path.startswith('/tiles/'):
                tile = parse_tile_path(self.path)
                data = fetch_tile(*tile) if tile else None
                if tile is None:
                    self.send_response(400)
                    self.end_headers()
                elif data is None:
                    self.send_response(503)  # offline and not cached yet
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'public, max-age=604800')
                    self.end_headers()
                    self.wfile.write(data)
                return

            # If the requested path is not a file, return index.html
            path = self.translate_path(self.path)
            if not os.path.isfile(path):
                self.path = '/index.html'
            return super().do_GET()
    
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        # Without SO_REUSEADDR a restart (manager cycle or the disable/enable toggle)
        # can hit "Address already in use" while the old socket sits in TIME_WAIT,
        # crash-looping the daemon until the kernel releases the port.
        allow_reuse_address = True

    with ThreadingHTTPServer(("", PORT), SPAHandler) as httpd:
        logging.info(f"[+] OpenRivian Web Dashboard serving at port {PORT}")
        httpd.serve_forever()

if __name__ == '__main__':
    main()
