from flask import Flask, request, render_template_string, send_from_directory

app = Flask(__name__)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('dist/assets', filename)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory("dist", "index.html")


if __name__ == '__main__':
    app.run(debug=True)