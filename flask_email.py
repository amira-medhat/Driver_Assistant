# from flask import Flask, jsonify, request
# import smtplib
# import ssl
# from email.mime.text import MIMEText
# from waitress import serve

# app = Flask(__name__)

# @app.route("/send_email", methods=["POST"])
# def send_email():
#     data = request.get_json()
#     livestreaming_link = data.get("link", "")
#     location = data.get("location", "Unknown location")

#     sender_email = "amiramedhat2016@gmail.com"
#     receiver_email = "amira.hassan02@eng-st.cu.edu.eg"
#     app_password = "kdek cgdc yybj hcfg"  # ✅ Use Gmail App Password
#     subject = "🚨 Driver Unresponsive Alert"
    
#     body = f"""
#     <html>
#     <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
#         <div style="max-width: 600px; margin: 30px auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); overflow: hidden;">
#         <div style="background-color: #dc3545; padding: 20px;">
#             <h2 style="color: #ffffff; margin: 0;">🚨 Driver Safety Alert</h2>
#         </div>
#         <div style="padding: 25px;">
#             <p style="font-size: 16px; color: #333;">
#                 <strong>Alert:</strong> The driver appears to be <span style="color: red;"><strong>unresponsive</strong></span>. Immediate action is recommended.
#             </p>
#             <p style="font-size: 15px; color: #555;">
#                 <strong>Last known location:</strong> {location}
#             </p>
#             <p style="font-size: 15px; color: #555;">
#                 Please try contacting the driver. If unreachable, check the live stream below.
#             </p>
#             <div style="text-align: center; margin: 30px 0;">
#                 <a href="{livestreaming_link}" target="_blank" 
#                 style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 5px;">
#                     ▶️ View Live Stream
#                 </a>
#             </div>
#             <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
#             <p style="font-size: 13px; color: #888; text-align: center;">
#                 Sent automatically by your Driver Monitoring System.<br>
#                 Do not reply to this email.
#             </p>
#         </div>
#         </div>
#     </body>
#     </html>
#     """

#     msg = MIMEText(body, "html")
#     msg["Subject"] = subject
#     msg["From"] = sender_email
#     msg["To"] = receiver_email

#     try:
#         with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
#             server.login(sender_email, app_password)
#             server.send_message(msg)
#         return jsonify({"status": "Email sent successfully"})
#     except Exception as e:
#         return jsonify({"error": str(e)})

# if __name__ == "__main__":
#     serve(app, host="0.0.0.0", port=5000)
from flask import Flask, request, jsonify
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)

@app.route("/send_email", methods=["POST"])
def send_email():
    data = request.get_json()
    youtube_link = data.get("link", "")
    location = data.get("location", "Unknown location")

    sender_email = "amiramedhat2016@gmail.com"
    receiver_email = "amira.hassan02@eng-st.cu.edu.eg"
    app_password = "kdek cgdc yybj hcfg"  # ✅ Gmail App Password
    subject = "🚨 Driver Unresponsive Alert"

    # Plain text version (updated to match image content)
    text = f"""\
🚨 Driver Safety Alert

Alert: The driver appears to be unresponsive. Immediate action is recommended.

Last known location: {location}

Please try contacting the driver. If unreachable, check the live stream below.

Live stream: {youtube_link}

Sent automatically by your Driver Monitoring System.
Do not reply to this email.
"""

    # HTML version (styled like your image)
    html = f"""\
<html>
<body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
  <div style="max-width: 600px; margin: auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
    <div style="background-color: #dc3545; color: white; padding: 16px 24px;">
      <h2 style="margin: 0;">🚨 Driver Safety Alert</h2>
    </div>
    <div style="padding: 24px;">
      <p><strong>Alert:</strong> The driver appears to be <span style="color: red;"><strong>unresponsive</strong></span>. Immediate action is recommended.</p>
      <p><strong>Last known location:</strong> {location}</p>
      <p>Please try contacting the driver. If unreachable, check the live stream below.</p>
      <div style="text-align: center; margin-top: 24px;">
        <a href="{youtube_link}" target="_blank" style="background-color: #007bff; color: white; padding: 12px 20px; border-radius: 6px; text-decoration: none; display: inline-block; font-weight: bold;">
          ▶️ View Live Stream
        </a>
      </div>
      <hr style="margin-top: 32px;">
      <p style="font-size: 12px; color: #666; text-align: center;">
        Sent automatically by your Driver Monitoring System.<br>
        Do not reply to this email.
      </p>
    </div>
  </div>
</body>
</html>
"""

    # Create message with both plain text and HTML parts
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = "Driver Monitoring System <sender_email>"
    msg["To"] = receiver_email

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return jsonify({"status": True})
    except Exception as e:
        return jsonify({"status": False, "error": str(e)})

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)

