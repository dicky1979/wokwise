#!/usr/bin/env python3
"""
WokWise Web Server — serves frontend + API
"""
import json
import os
import sys
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import WokWiseEngine, load_all_recipes, TEMPLATE_RECIPES

engine = WokWiseEngine()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_FILE = os.path.join(BASE_DIR, "recipes_custom.json")

def save_recipe(key, recipe):
    data = {}
    if os.path.exists(CUSTOM_FILE):
        with open(CUSTOM_FILE) as f:
            data = json.load(f)
    data[key] = recipe
    with open(CUSTOM_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 全局重新加载
    global TEMPLATE_RECIPES
    TEMPLATE_RECIPES = load_all_recipes()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 静态文件
        if path == "/" or path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif path.startswith("/api/"):
            self._handle_api(path, params)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/upload":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            key = body.get("key", "")
            recipe = body.get("recipe", {})
            if key and recipe:
                save_recipe(key, recipe)
                self._json({"success": True})
            else:
                self._json({"success": False, "error": "missing fields"})
        else:
            self._json({"error": "not found"})

    def _handle_api(self, path, params):
        if path == "/api/recipe":
            q = params.get("q", [""])[0]
            result = engine.get_recipe(q)
            if "error" in result:
                for key, r in TEMPLATE_RECIPES.items():
                    if q.lower() in r["name"].lower():
                        result = engine._adapt_recipe(r)
                        break
            self._json(result)
        elif path == "/api/recipes":
            self._json(TEMPLATE_RECIPES)
        elif path == "/api/stove":
            stove = params.get("type", ["gas"])[0]
            result = engine.set_kitchen(stove)
            self._json({"status": result})
        else:
            self._json({"error": "unknown endpoint"})

    def _serve_file(self, filename, mime):
        fpath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(fpath):
            self.send_response(404)
            self.end_headers()
            return
        with open(fpath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    port = 8765
    print(f"  WokWise running at: http://127.0.0.1:{port}")
    print(f"  Browse recipes · Search · Upload your own")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
