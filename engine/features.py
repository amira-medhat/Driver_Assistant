# Import modules

import pygame  # For playing audio feedback sounds
import eel     # Enables Python-JavaScript communication (used for frontend integration)
import os      # For file system operations
import pywhatkit as kit  # (not used here, could be removed or used for future WhatsApp automation)
import re      # Regular expressions (not used here directly)
import pyautogui  # Automates GUI actions like mouse clicks and keypresses
import subprocess  # For running shell commands
import time  # For time delays
import webbrowser  # For opening URLs
from urllib.parse import quote  # For encoding URLs/messages
from engine.command import AudioManager  # Custom audio manager for voice feedback
import json
from engine.command import state




# ===================== UI Audio Feedback Functions =====================

@eel.expose
def playAssistantSound():
    """
    Plays a sound when the assistant activates (used on start).
    """
    music_path = "www//assets//audio//start_sound.mp3"  # Path to start sound
    pygame.mixer.init()  # Initialize the mixer
    pygame.mixer.music.load(music_path)  # Load sound file
    pygame.mixer.music.play()  # Play sound

    # Wait until sound finishes playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)  # Poll every 10 ticks


@eel.expose
def playClickSound():
    """
    Plays a short sound when user clicks something.
    """
    music_path = "www//assets//audio//click_sound.wav"  # Path to click sound
    pygame.mixer.init()
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.play()

    # Wait until sound finishes playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)


# ===================== Windows-Based WhatsApp Messaging/Calling =====================

def send_whatsApp_msg(mobile_no, message, flag, name):
    """
    Opens WhatsApp on Windows and sends a message or makes a call.
    
    Parameters:
        mobile_no (str): Phone number in international format (e.g., +201234567890)
        message (str): Message to send (for text)
        flag (str): 'message', 'call', or anything else (treated as video call)
        name (str): Contact's name (used for speaking responses, if re-enabled)
    """
    audio = AudioManager()  # For voice responses (currently not used here)

    # Encode the message for URL format
    encoded_message = quote(message)
    
    # Construct the WhatsApp URL for sending message
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"
    
    # Full Windows command to open WhatsApp via URL
    full_command = f'start "" "{whatsapp_url}"'
    
    subprocess.run(full_command, shell=True)  # Run command in shell
    time.sleep(6)  # Give time for WhatsApp window to open and load

    if flag == 'message':
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.hotkey('alt', 'f4')  # Close the window after sending

    elif flag == 'call':
        pyautogui.click(x=1807, y=114)  # Voice call button (adjust coordinates if needed)
        time.sleep(7)  # Wait for 50 seconds
        pyautogui.hotkey('alt', 'f4')  # Close the window after the call

    else:
        pyautogui.click(x=1200, y=100)  # Video call button (adjust coordinates)
        time.sleep(1)

@eel.expose
def OpenGps(query):

    global maps_process
    audio = AudioManager()

    if query:
        if "gps" in query or "map" in query or "location" in query:
            audio.speak("Opening your location on Google Maps")
            
            # Load coordinates from JSON
            try:
                with open("location.json", "r") as f:
                    data = json.load(f)
                    lat = data.get("latitude")
                    lon = data.get("longitude")

                    if lat and lon:
                        map_url = f"https://www.google.com/maps?q={lat},{lon}"
                        #os.system(f"xdg-open '{map_url}'")  # Linux command to open browser
                        maps_process = subprocess.Popen(["cmd", "/c", "start", "", map_url])
                        #maps_process = subprocess.Popen(["xdg-open", map_url])
                    else:
                        audio.speak("Location coordinates not available.")
            except Exception as e:
                print(f"[Location Error] {e}")
                audio.speak("Couldn't open Google Maps.")
        
        else:
            audio.speak(f"Opening {query}")
            os.system(f"bash -i -c 'start {query}'")

    else:
        audio.speak("Please tell me what to open")

@eel.expose
def CloseMaps():
    audio = AudioManager()
    try:
        # Close any window that has "Google Maps" or "maps" in the title
        os.system("wmctrl -c 'Google Maps'")
        os.system("wmctrl -c 'maps'")
        audio.speak("Closed Google Maps window.")
    except Exception as e:
        print(f"[Error closing maps]: {e}")
        audio.speak("Couldn't close Google Maps.")







