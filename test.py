from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='dist', static_url_path='')

# Serve static files (CSS, JS, etc.)
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('dist/assets', filename)

# Serve the main HTML file for all routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # Serve static files directly
    if path and (path.startswith('assets/') or '.' in path):
        return send_from_directory(app.static_folder, path)
    # Otherwise, return the React app's index.html
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True)