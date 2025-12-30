import os
import smtplib
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")


# ===============================
# SERVE FRONTEND
# ===============================
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# ===============================
# EMAIL SENDER
# ===============================
def send_email(data, attachments, ip):
    msg = EmailMessage()
    msg["Subject"] = "NEW PETITION SUBMISSION – TMT Travels (Allegation)"
    msg["From"] = EMAIL_USER
    msg["To"] = RECEIVER_EMAIL

    msg.set_content(f"""
NEW ALLEGATION SUBMISSION (FOR LEGAL REVIEW)

Full Name: {data['full_name']}
Email Address: {data['email']}
Phone Number: {data['phone']}

Date of Payment: {data['payment_date']}
Account Name Paid Into: {data.get('account_name', 'Not provided')}
Account Number Paid Into: {data.get('account_number', 'Not provided')}

Submitted At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
IP Address: {ip}

This submission represents an allegation provided by a complainant
for legal review by Eluyefa Chambers on behalf of Mr Scott Iguma.
""")

    for file_info in attachments:
        with open(file_info["path"], "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=file_info["original_name"]
            )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)


# ===============================
# FORM SUBMISSION
# ===============================
@app.route("/submit", methods=["POST"])
def submit_petition():
    try:
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        payment_date = request.form.get("payment_date")
        account_name = request.form.get("account_name")
        account_number = request.form.get("account_number")

        proofs = request.files.getlist("proof")

        if not full_name or not email or not phone or not payment_date or not proofs:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        saved_files = []
        for proof in proofs:
            filename = f"{int(datetime.now().timestamp())}_{proof.filename}"
            path = os.path.join(UPLOAD_FOLDER, filename)
            proof.save(path)
            saved_files.append({"path": path, "original_name": proof.filename})

        send_email(
            data={
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "payment_date": payment_date,
                "account_name": account_name,
                "account_number": account_number
            },
            attachments=saved_files,
            ip=request.remote_addr
        )

        return jsonify({"success": True})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"success": False}), 500


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
