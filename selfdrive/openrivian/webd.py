#!/usr/bin/env python3
import os
import http.server
import socketserver
import logging
import threading

PORT = 8081

ROUTE_CACHE = []
ROUTE_CACHE_LOCK = threading.Lock()

ROUTES_PATH = "/data/media/0/realdata/"

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

            # If the requested path is not a file, return index.html
            path = self.translate_path(self.path)
            if not os.path.isfile(path):
                self.path = '/index.html'
            return super().do_GET()
    
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True

    with ThreadingHTTPServer(("", PORT), SPAHandler) as httpd:
        logging.info(f"[+] OpenRivian Web Dashboard serving at port {PORT}")
        httpd.serve_forever()

if __name__ == '__main__':
    main()
