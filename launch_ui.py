import http.server
import socketserver
import webbrowser
import threading
import os
import time

PORT = 8080
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")

class RobustTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_server():
    os.chdir(DIRECTORY)
    Handler = http.server.SimpleHTTPRequestHandler
    global PORT
    for port in range(8080, 8095):
        try:
            with RobustTCPServer(("", port), Handler) as httpd:
                PORT = port
                print(f"Serving UI at http://localhost:{PORT}")
                httpd.serve_forever()
            break
        except OSError:
            continue

if __name__ == "__main__":
    if not os.path.exists(DIRECTORY):
        print(f"Error: Directory '{DIRECTORY}' not found.")
        exit(1)
        
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for the server to bind and update PORT
    time.sleep(1)
    
    print(f"Opening browser at http://localhost:{PORT} ...")
    webbrowser.open(f"http://localhost:{PORT}")
    
    print(f"Server is running on port {PORT}. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server.")
