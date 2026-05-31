#!/data/data/com.termux/files/usr/bin/python3
"""Voice Note GUI Server — local web player with full controls."""
import http.server
import json
import os
import subprocess
import urllib.parse
import threading

PORT = 8765
VN_DIR = os.path.expanduser("~/Projex")

def get_duration(filepath):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 0

class VNHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=VN_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/' or self.path == '/vn-gui.html':
            self.path = '/vn-gui.html'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            with open(os.path.join(VN_DIR, 'vn-gui.html'), 'rb') as f:
                self.wfile.write(f.read())
            return
        elif self.path == '/api/files':
            self.send_json(self.list_files())
            return
        elif self.path.startswith('/api/file/'):
            filename = urllib.parse.unquote(self.path[len('/api/file/'):])
            filepath = os.path.join(VN_DIR, filename)
            if os.path.exists(filepath):
                self.serve_audio(filepath)
            else:
                self.send_error(404)
            return
        else:
            self.send_error(404)
        return

    def list_files(self):
        files = []
        for f in sorted(os.listdir(VN_DIR)):
            if f.endswith('.mp3'):
                path = os.path.join(VN_DIR, f)
                dur = get_duration(path)
                files.append({
                    'name': f,
                    'duration': round(dur, 1),
                    'size': round(os.path.getsize(path) / 1024, 0)
                })
        return files

    def serve_audio(self, filepath):
        self.send_response(200)
        self.send_header('Content-Type', 'audio/mpeg')
        self.send_header('Content-Length', os.path.getsize(filepath))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass  # Silence logs

if __name__ == '__main__':
    server = http.server.HTTPServer(('127.0.0.1', PORT), VNHandler)
    print(f"🎵 Voice Note GUI: http://127.0.0.1:{PORT}")
    print("   Open in your browser to play voice notes")
    print("   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.shutdown()
