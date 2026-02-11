from flask import Flask, jsonify, render_template
import monitor
import os
import logging

# Disable Flask logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/snapshot")
def get_snapshot():
    return jsonify(monitor.get_snapshot())

@app.route("/api/files")
def get_files():
    try:
        files = os.listdir("files")
        file_list = []
        for f in files:
            path = os.path.join("files", f)
            size = os.path.getsize(path)
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            file_list.append({"name": f, "size": size_str})
        return jsonify(file_list)
    except Exception:
        return jsonify([])

def run():
    print("[+] Dashboard running on http://localhost:8000")
    # Change to project directory to avoid .env permission issues
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # Set environment to prevent Flask from loading parent .env
    os.environ['FLASK_ENV'] = 'production'
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

if __name__ == "__main__":
    run()
