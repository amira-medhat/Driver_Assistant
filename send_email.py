"""
@file send.py
@brief Sends a styled HTML emergency alert email with a live stream URL and live location map.
"""

# Import required modules
import smtplib
from email.message import EmailMessage
import requests
from config import *  # Includes: SENDER_EMAIL, APP_PASSWORD, LOCATION_API_KEY

import pywifi
import time
import json


class LocationProvider:
    def __init__(self):
        self.api_key = LOCATION_API_KEY

    def scan_wifi_windows(self):
        """
        Scan nearby Wi-Fi networks using pywifi (Windows).
        Returns a list of dicts: [{mac, signalStrength}, ...]
        """
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]

        iface.scan()
        time.sleep(3)  # wait for scan to complete
        results = iface.scan_results()

        wlan_data = []
        for network in results:
            mac = network.bssid
            signal = network.signal  # RSSI in dBm
            wlan_data.append({
                "mac": mac,
                "signalStrength": signal
            })

        return wlan_data




    def get_current_location(self):
        try:
            with open('location.json', 'r') as f:
                data = json.load(f)

            lat_str = data.get("latitude")
            lon_str = data.get("longitude")
            address = data.get("address", "Unknown location")

            lat = float(lat_str)
            lon = float(lon_str)
            map_url = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"

            return lat, lon, address, map_url

        except (ValueError, TypeError) as ve:
            print("⚠ Location values are invalid:", ve)
            return None, None, "Invalid location data", "#"

        except Exception as e:
            print("⚠ Failed to get location:", e)
            return None, None, "Location unavailable", "#"





# === EMAIL ALERT FUNCTION ===

def send_alert_email(url, to_email):
    """
    Sends a styled HTML email alert with the given live stream URL and current location map.
    """

    location_provider = LocationProvider()
    lat, lon, address, map_url = location_provider.get_current_location()

    print(f"[DEBUG] Location from LocationProvider: lat={lat}, lon={lon}")

    if lat is not None and lon is not None:
        location = f"{lat:.6f}, {lon:.6f}"
        # ✅ Use the correct format for pinning exact location
        map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    else:
        location = "Unknown"
        map_url = "https://www.google.com/maps"

    msg = EmailMessage()
    msg['Subject'] = '🚨 Emergency Alert: Driver Unresponsive'
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email

    msg.set_content(f'''
    ALERT! The driver may be asleep.
    Location: {location}
    Stream: {url}
    Live Map: {map_url}
    ''')

    html_content = f"""
    <html>
    <body style="margin: 0; padding: 0; background-color: #f9f9f9; font-family: 'Segoe UI', sans-serif;">
        <div style="max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); overflow: hidden;">

            <div style="background: #1a1a2e; padding: 24px; text-align: center;">
                <h2 style="color: #ffffff; margin: 0;">🚨 Driver Safety Alert</h2>
            </div>

            <div style="padding: 30px;">
                <p style="font-size: 17px; color: #222;">
                    <strong>Alert:</strong> The driver appears to be <span style="color: #e63946;"><strong>unresponsive</strong></span>.
                </p>

                <p style="font-size: 15px; color: #444;">
                    <strong>Last known location:</strong> <span style="color: #1a8cff;">{location}</span>
                </p>

                <div style="text-align: center; margin: 20px 0;">
                    <a href="{map_url}" target="_blank"
                    style="background: #ffc107; color: black; padding: 12px 24px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 30px;">
                    📍 Live Location
                    </a>
                </div>

                <div style="text-align: center; margin: 20px 0;">
                    <a href="{LIVE_STREAM_URL}" target="_blank"
                    style="background: #1a8cff; color: white; padding: 14px 28px; text-decoration: none; font-weight: bold; font-size: 16px; border-radius: 30px;">
                    ▶️ Live Streaming
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
