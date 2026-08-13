from flask import Flask, render_template, request
import smtplib
import os
from email.message import EmailMessage

app = Flask(__name__, static_folder="static", template_folder="templates")

# Home page
@app.route("/")
def home():
    return render_template("index.html")


# CONTACT FORM
@app.route("/submit", methods=["GET", "POST"])
def submit():

    # If you open /submit directly in your browser
    if request.method == "GET":
        return "Submit route is working. Please use the contact form to send a message."

    name = request.form.get("name", "")
    email = request.form.get("email", "")
    message = request.form.get("message", "")

    # These are stored in Render Environment Variables
    MY_EMAIL = os.environ.get("MY_EMAIL")
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
    SENDER_APP_PASSWORD = os.environ.get("SENDER_APP_PASSWORD")

    # Check that Render has the variables
    if not MY_EMAIL:
        return "ERROR: MY_EMAIL is not set in Render Environment Variables.", 500

    if not SENDER_EMAIL:
        return "ERROR: SENDER_EMAIL is not set in Render Environment Variables.", 500

    if not SENDER_APP_PASSWORD:
        return "ERROR: SENDER_APP_PASSWORD is not set in Render Environment Variables.", 500

    # Create the email
    msg = EmailMessage()

    msg["Subject"] = "New EditPro Request"
    msg["From"] = SENDER_EMAIL
    msg["To"] = MY_EMAIL
    msg["Reply-To"] = email

    msg.set_content(
        f"""
New request from EditPro website

Name: {name}
Email: {email}

What they need:
{message}
"""
    )

    try:

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:

            smtp.login(
                SENDER_EMAIL,
                SENDER_APP_PASSWORD
            )

            smtp.send_message(msg)

        return "Your request has been sent successfully!"

    except Exception as e:

        print("EMAIL ERROR:", e)

        return f"EMAIL ERROR: {e}", 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
