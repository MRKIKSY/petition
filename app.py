import os
import smtplib
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime
import traceback

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")


# ===============================
# BASIC ROUTES
# ===============================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/favicon.ico")
def favicon():
    return "", 204


# ===============================
# EMAIL FUNCTION (SAFE)
# ===============================
def send_email_safe(data, attachments, ip):
    try:
        print("📧 Attempting to send email...")

        msg = EmailMessage()
        msg["Subject"] = "NEW PETITION SUBMISSION – TMT Travels (Allegation)"
        msg["From"] = EMAIL_USER
        msg["To"] = RECEIVER_EMAIL

        msg.set_content(f"""
NEW ALLEGATION SUBMISSION (FOR LEGAL REVIEW)

Full Name: {data['full_name']}
Email: {data['email']}
Phone: {data['phone']}
Date Paid: {data['payment_date']}
Account Name: {data.get('account_name')}
Account Number: {data.get('account_number')}

IP Address: {ip}
Submitted At: {datetime.utcnow()}
""")

        for f in attachments:
            with open(f["path"], "rb") as file:
                msg.add_attachment(
                    file.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=f["original_name"]
                )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        print("✅ Email sent")

    except Exception as e:
        print("❌ EMAIL FAILED")
        traceback.print_exc()


# ===============================
# SUBMIT ROUTE (NEVER 500)
# ===============================
@app.route("/submit", methods=["POST"])
def submit():
    try:
        print("📩 New submission received")

        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        payment_date = request.form.get("payment_date")

        proofs = request.files.getlist("proof")

        if not all([full_name, email, phone, payment_date]):
            return jsonify({"success": False, "error": "Missing fields"}), 400

        saved_files = []

        for proof in proofs:
            if proof.filename:
                filename = f"{int(datetime.now().timestamp())}_{proof.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                proof.save(path)
                saved_files.append({
                    "path": path,
                    "original_name": proof.filename
                })

        send_email_safe(
            data={
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "payment_date": payment_date,
                "account_name": request.form.get("account_name"),
                "account_number": request.form.get("account_number")
            },
            attachments=saved_files,
            ip=request.remote_addr
        )

        # ALWAYS return success to frontend
        return jsonify({"success": True})

    except Exception:
        print("❌ SUBMIT HANDLER FAILED")
        traceback.print_exc()
        return jsonify({"success": False}), 200


# ===============================
# TEST EMAIL ENDPOINT
# ===============================
@app.route("/test-email")
def test_email():
    send_email_safe(
        data={
            "full_name": "Test",
            "email": "test@test.com",
            "phone": "000",
            "payment_date": "2025-01-01",
            "account_name": "Test",
            "account_number": "123"
        },
        attachments=[],
        ip="127.0.0.1"
    )
    return "Email test attempted"


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
