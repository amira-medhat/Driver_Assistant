"""
@file send.py
@brief Sends a styled HTML emergency alert email with a live stream URL and live location map.
"""

import smtplib
from email.message import EmailMessage
import geocoder
from config import *




# === LOCATION UTILITY ===

def get_current_location():
    try:
        g = geocoder.ip('me')
        lat, lon = g.latlng if g.latlng else (None, None)
        city = g.city or "Unknown city"
        country = g.country or "Unknown country"
        map_url = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else "#"
        return f"{city}, {country}", map_url
    except Exception as e:
        print("⚠️ Failed to get location:", e)
        return "Location unavailable", "#"


# === EMAIL SENDER ===

def send_alert_email(url, to_email):
    """
    Sends a styled HTML email alert with the given live stream URL and location map.
    """
    location, map_url = get_current_location()

    msg = EmailMessage()
    msg['Subject'] = '🚨 Emergency Alert: Driver Unresponsive'
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email

    # Plaintext fallback
    msg.set_content(f'''
    ALERT! The driver may be asleep.
    Location: {location}
    Stream: {url}
    Live Map: {map_url}
    ''')

    # HTML content
    html_content = f"""
    <html>
    <body style="margin: 0; padding: 0; background-color: #f9f9f9; font-family: 'Segoe UI', sans-serif;">
        <div style="max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); overflow: hidden;">

            <!-- Header -->
            <div style="background: #1a1a2e; padding: 24px; text-align: center;">
                <h2 style="color: #ffffff; margin: 0;">🚨 Driver Safety Alert</h2>
            </div>

            <!-- Body -->
            <div style="padding: 30px;">
                <p style="font-size: 17px; color: #222;">
                    <strong>Alert:</strong> The driver appears to be <span style="color: #e63946;"><strong>unresponsive</strong></span>.
                </p>
                <p style="font-size: 15px; color: #444;">
                    <strong>Last known location:</strong> <span style="color: #1a8cff;">{location}</span>
                </p>

                <!-- Live Location Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{map_url}" target="_blank"
                    style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 30px;">
                    📍 View Live Location
                    </a>
                </div>

                <!-- Stream Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url}" target="_blank"
                    style="background: #1a8cff; color: white; padding: 14px 28px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 30px;">
                    ▶️ View Live Stream
                    </a>
                </div>

                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                <p style="font-size: 13px; color: #888; text-align: center;">
                    Sent automatically by your Driver Monitoring System.<br>
                    This is an automated alert — please do not reply.
                </p>
            </div>
        </div>
    </body>
    </html>
    """


    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
            print("✅ Alert email sent successfully!")
    except Exception as e:
        print("❌ Failed to send email:", e)

