
from flask import Flask, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Content Planner e-book sales page
@app.route("/content-planner")
def content_planner():
    return render_template("content_planner.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
