from flask import Flask, render_template, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')

# Home page
@app.route("/")
def home():
    return render_template("index.html")

# Serve images (if needed)
@app.route('/images/<path:filename>')
def images(filename):
    return send_from_directory('static/images', filename)

# Serve JS (if needed)
@app.route('/js/<path:filename>')
def js_files(filename):
    return send_from_directory('static/js', filename)

if __name__ == "__main__":
    # Host 0.0.0.0 so it works on most cloud deployments
    app.run(host="0.0.0.0", port=5000, debug=True)
