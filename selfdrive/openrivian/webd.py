#!/usr/bin/env python3
import os
import http.server
import socketserver
import logging

PORT = 8081

def main():
    logging.basicConfig(level=logging.INFO)
    
    # Path to the compiled React app
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard/dist")
    
    if not os.path.exists(web_dir):
        logging.error(f"[-] Web directory not found at {web_dir}. Please run 'npm run build' inside the dashboard directory first.")
        return
        
    os.chdir(web_dir)
    
    # Simple HTTP request handler
    Handler = http.server.SimpleHTTPRequestHandler
    
    # To handle React Router / single page app refresh nicely, we can override do_GET:
    class SPAHandler(Handler):
        def do_GET(self):
            # If the requested path is not a file, return index.html
            path = self.translate_path(self.path)
            if not os.path.isfile(path):
                self.path = '/index.html'
            return super().do_GET()
    
    with socketserver.TCPServer(("", PORT), SPAHandler) as httpd:
        logging.info(f"[+] OpenRivian Web Dashboard serving at port {PORT}")
        httpd.serve_forever()

if __name__ == '__main__':
    main()
