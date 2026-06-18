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
            if self.path == '/offer':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    import urllib.request
                    import json
                    
                    # Parse incoming React SDP offer
                    client_offer = json.loads(post_data.decode('utf-8'))
                    
                    # webrtcd expects a fully populated StreamRequestBody
                    webrtcd_payload = {
                        "sdp": client_offer.get("sdp", ""),
                        "cameras": ["road"],
                        "bridge_services_in": [],
                        "bridge_services_out": ["carState", "modelV2"]
                    }
                    webrtcd_post_data = json.dumps(webrtcd_payload).encode('utf-8')
                    
                    # Proxy the request to local webrtcd (port 5001)
                    req = urllib.request.Request("http://localhost:5001/stream", data=webrtcd_post_data, headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req) as response:
                        res_body = response.read()
                        self.send_response(response.getcode())
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(res_body)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f'{{"error": "HTTP Error 500: {str(e)}"}}'.encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()

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
