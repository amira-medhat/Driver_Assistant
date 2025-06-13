import sys
import traceback

def catch_all_exceptions(exctype, value, tb):
    print("💥 Uncaught exception:")
    traceback.print_exception(exctype, value, tb)
    input("\n[EXIT] Press Enter to close...")

sys.excepthook = catch_all_exceptions
import eel
import webbrowser
import threading

from engine.features import *
from engine.command import *

# Initialize Eel with your frontend folder
eel.init("www")

playAssistantSound()

# ✅ Open in default browser
webbrowser.open_new("http://localhost:8000/index.html")

# Start monitoring in a background thread
threading.Thread(target=monitoring_loop, daemon=True).start()

# Start the Eel server (no browser popup from Eel itself)
eel.start('index.html', mode=None, host='localhost', port=8000, block=True)



