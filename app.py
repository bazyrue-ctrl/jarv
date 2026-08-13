from flask import Flask, render_template, request
import smtplib
from email.message import EmailMessage

app = Flask(__name__, static_folder="static", template_folder="templates")

# Home page
@app.route("/")
def home():
    return render_template("index.html")


# CONTACT FORM - ADDED
@app.route("/submit", methods=["POST"])
def submit():

    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    # WRITE YOUR EMAIL HERE
    MY_EMAIL = "ronahhyo@gmail.com"

    # EMAIL ACCOUNT THAT SENDS THE MESSAGE
    SENDER_EMAIL = "YOUR_EMAIL@gmail.com"

    # GMAIL APP PASSWORD
    SENDER_APP_PASSWORD = "zcah azgy nlmq jkxm"

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
            smtp.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp.send_message(msg)

        return "Your request has been sent successfully!"

    except Exception as e:
        print("EMAIL ERROR:", e)
        return "There was a problem sending your request.", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
