import os
import sys
import traceback
from gtts import gTTS  # Google Text-to-Speech
import pygame
import speech_recognition as sr
import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import eel
import time
import ollama
import threading
import json
import asyncio
import edge_tts
from datetime import datetime
import geocoder
import webbrowser
import geopy
from geopy.geocoders import Nominatim
from pydub import AudioSegment
from pydub.playback import play
import io

current_mode = "monitoring" # initial mode
mic_pressed = False
json_file_path = "data/driver_alert.json"  # path where Jetson Nano writes JSON
location_override = None

    
def generate_initial_context():
    global location_override
    now = datetime.now()
    current_date = now.strftime("%A, %B %d, %Y")
    current_time = now.strftime("%I:%M %p")

    # Get approximate location (based on IP)
    try:
        g = geocoder.ip('me')
        city = g.city or "an unknown city"
        country = g.country or "an unknown country"
        location_text = f"You are currently in {city}, {country}."
        if location_override:
            location_text = f"You are currently at {location_override}."
    except:
        location_text = "Location is unavailable."

    system_prompt = f"""You are a helpful driving assistant.
Today is {current_date} and the time is {current_time}.
{location_text}
You do functions like providing him current location, current time, traffic and weather info, estimated arrival time to destinations and routing steps to these destinations.
You also talk with him if he feels sleepy or suffers fatigue.
Only respond in 1–2 sentences unless instructed otherwise.
"""

    return {"role": "system", "content": system_prompt}

conversation_history = [generate_initial_context()]

def estimate_tokens(text):
    return len(text.split()) * 1.3  # ≈ 1.3 tokens per word (safe estimate)

def trim_history(history, max_tokens=7000):  # Leave room for response
    total_tokens = 0
    trimmed = []

    # Keep system message at the top
    if history and history[0]['role'] == 'system':
        trimmed.append(history[0])
        history = history[1:]

    # Add from most recent to oldest, until we reach token limit
    for msg in reversed(history):
        tokens = estimate_tokens(msg['content'])
        if total_tokens + tokens <= max_tokens:
            trimmed.insert(1, msg)  # insert after system message
            total_tokens += tokens
        else:
            break  # stop when too many

    return trimmed



@eel.expose
def ReceiveLocation(lat, lon):
    global location_override, conversation_history
    try:
        geolocator = Nominatim(user_agent="driver_assistant")
        location = geolocator.reverse((lat, lon), language="en")
        address = location.address
        print(f"[📍] Precise location: {address}")
        
        location_override = address
        # Update initial assistant prompt with accurate location
        # Only replace if history exists
        if conversation_history and conversation_history[0]["role"] == "system":
            conversation_history[0] = generate_initial_context()
        else:
            print("[WARN] Couldn't update system message — history not ready.")
        
    except Exception as e:
        print(f"[ERROR] Failed to reverse geocode: {e}")



def handle_navigation(query):
    # Extract destination
    destination = query.lower().replace("navigate to", "").strip()
    if destination:
        eel.DisplayMessage(f"Opening directions to {destination.title()}...")
        speak(f"Opening directions to {destination.title()}...")

        # Open in default browser
        webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={destination.replace(' ', '+')}")
    else:
        speak("Where would you like to go?")




################## another way for text to speech #####################
# import pyttsx3
# def speak(text):
#     # Generate speech with gTTS
#     engine = pyttsx3.init()
#     #voices = engine.getProperty('voices')
#     #engine.setProperty('voice', voices[0].id)
#     #print(voices)
#     engine.setProperty('rate', 125)
#     engine.say(text)
#     engine.runAndWait()

# speak("hello nada how are you today ?") 


@eel.expose
def speak(text):
    print(f"[TTS] Speaking: {text}")
    asyncio.run(edge_speak(text))

        
async def edge_speak(text, voice="en-US-AriaNeural"):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    mp3_bytes = b""

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_bytes += chunk["data"]

    # Convert to playable audio
    audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    play(audio)

# model = whisper.load_model("large")  # You can also use "base" or "medium" if memory is tight

# def record_audio(filename="input.wav", duration=5, fs=16000):
#     print("[🎙️] Recording audio...")
#     audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
#     sd.wait()
#     write(filename, fs, audio)
#     print("[✅] Saved:", filename)

# def transcribe_with_whisper(filename="input.wav", lang="en"):
#     print("[🔍] Transcribing with Whisper...")
#     result = model.transcribe(filename, language=lang)
#     text = result["text"].strip().lower()
#     print(f"[🗣️ STT]: {text}")
#     return text

@eel.expose
def takecommand(timeout=15, phrase_time_limit=20):
    """Listens for speech with timeout and returns recognized text or 'none'."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("[STT] Listening for a command...")
        eel.DisplayMessage("[Listening for command...]")

        # Adjust to ambient noise
        recognizer.adjust_for_ambient_noise(source)

        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("[STT] Recognizing...")
            eel.DisplayMessage("[Recognizing...]")

            query = recognizer.recognize_google(audio, language="en")
            print(f"[STT] You said: {query}")
            return query.lower()

        except sr.WaitTimeoutError:
            print("[STT] No speech detected (timeout)")
            eel.DisplayMessage("[STT Timeout — no speech detected]")
            return "none"

        except sr.UnknownValueError:
            print("[STT] Could not understand the audio")
            eel.DisplayMessage("[Could not understand the audio]")
            return "none"

        except sr.RequestError:
            print("[STT] STT request failed (possibly no internet)")
            eel.DisplayMessage("[STT request failed (check internet)]")
            return "none"



@eel.expose
def PassToLlm():
    global mic_pressed, current_mode, conversation_history

    # Continue processing commands until the user issues an exit command
    while current_mode == "assistance":
        query = takecommand()  # Listen for a command
        print(f"[USER]: {query}")
        user_message = {"role": "user", "content": query}
        conversation_history.append(user_message)

        # If nothing was heard, notify the user and continue the loop
        if query == "none":
            eel.DisplayMessage("I didn't hear anything. Can you repeat that?")
            speak("I didn't hear anything. Can you repeat that?")
            time.sleep(0.5)
            continue  # Retry listening for a valid command

        # Check if the user wants to exit assistance mode
        if any(phrase in query for phrase in ["enable monitoring", "monitoring mode", "back to monitoring", "exit", "disable assistant", "monitoring", "disable assist"]):
            print("[DEBUG] Switching to monitoring mode.")
            eel.DisplayMessage("Got it!")
            speak("Got it!")
            eel.DisplayMessage("Switching to monitoring mode.")
            speak("Switching to monitoring mode.")
            current_mode = "monitoring"
            mic_pressed = False
            eel.ExitHood()
            break  # Exit the loop
        
        # Check for navigation command
        if query.lower().startswith("navigate to"):
            handle_navigation(query)
            continue  # skip sending to LLM, since we handled it

        # Otherwise, process the command via LLM
        try:
            safe_history = trim_history(conversation_history)
            response = ollama.chat(model='llama3.2', messages=safe_history)
            llama_response = response['message']['content']
            eel.DisplayMessage(llama_response)
            speak(llama_response)
            assistant_message = {"role": "assistant", "content": llama_response}
            conversation_history.append(assistant_message)
            
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            eel.DisplayMessage("Sorry, I couldn't process your request.")
            speak("Sorry, I couldn't process your request.")
            time.sleep(1)

    # End of assistance mode: now in monitoring mode.
    # (If the loop exits normally, we assume an exit command was given.)
    # Any necessary cleanup can be done here.



    
@eel.expose
def set_mic_pressed():
    global mic_pressed
    mic_pressed = True

    
@eel.expose
def ListenForWakeWord(wake_word="hey man"): 

    # global current_mode
    recognizer = sr.Recognizer()


    with sr.Microphone() as source:
        print("[Listening for wake word...]")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=7)
            transcript = recognizer.recognize_google(audio).lower()
            print(f"[DEBUG] Heard: {transcript}")

            if wake_word in transcript:
                eel.DisplayMessage("Hey driver, how can I help you?")
                speak("Hey driver, how can I help you?")
                time.sleep(0.5)
                return True

        except sr.WaitTimeoutError:
            print("[DEBUG] No speech detected in time.")
        except sr.UnknownValueError:
            print("[DEBUG] Could not understand the audio.")
        except sr.RequestError as e:
            print(f"[ERROR] Speech recognition failed: {e}")

    return False 

@eel.expose
def monitoring_loop():
    global current_mode, mic_pressed

    while True:
        # Enter assistant mode via wake word or mic
        if mic_pressed or (current_mode == "monitoring" and ListenForWakeWord()):
            current_mode = "assistance"
            eel.ShowHood()
            PassToLlm()
            continue
        
        if current_mode == "assistance":
            eel.ShowHood()
            PassToLlm()
            continue

        # Run only if in monitoring mode
        if current_mode == "monitoring" and not mic_pressed:
            if os.path.exists(json_file_path):
                with open(json_file_path, "r") as f:
                    data = json.load(f)

                    # Mode may change mid-read, check again
                    if current_mode != "monitoring":
                        continue

                    fatigue = data.get("Fatigue Alert", "").lower()
                    sleep = data.get("Sleep Alert", False)
                    action = data.get("Activity Alert", "").lower()
                    hands = data.get("HOW Alert", "").lower()
                    health = data.get("Health Alert", "").lower()
                    distraction = data.get("Distraction Alert", "").lower()

                    # Speak alerts only if still in monitoring mode
                    if current_mode != "monitoring":
                        continue

                    if fatigue == "on" or sleep:
                        speak("[ALERT] Fatigue or Sleep Alert detected.")
                        alert()
                    if action != "safe driving" and distraction == "on":
                        speak("please drive safely and focus on the road")
                    if hands == "off_wheel":
                        speak("Please keep your hands on the wheel")
                    if health == "on":
                        speak("Please take care as your heart rate is high. Take a break if needed")
                    if action == "eating":
                        speak("Please avoid eating while driving")
                    if action == "drinking":
                        speak("Please avoid drinking while driving")
                    if action in ["talking on the phone", "texting on the phone"]:
                        speak("Please avoid using phone while driving")

        time.sleep(1)



def alert():
    global current_mode
    current_mode = "fatigue_alert"
    eel.DisplayMessage("Are you okay? Can you hear me?")
    speak("Are you okay? Can you hear me?")
    time.sleep(0.5)
    eel.ShowHood()
    response = check_up(timeout=10)

    if response is None:
        eel.DisplayMessage("Dangerous! No response from driver.")
        speak("Dangerous! No response from driver.")
        time.sleep(0.5)
        BuzzerSound()
        current_mode = "monitoring"
        eel.ExitHood()
        return
    else:
        eel.DisplayMessage("Do you want to talk to me?")
        speak("Do you want to talk to me?")
        time.sleep(0.5)
        answer = check_up(timeout=10)
        if answer and "yes" in answer:
            eel.DisplayMessage("Okay, I'm here to help you.")
            speak("Okay, I'm here to help you.")
            time.sleep(0.25)
            eel.DisplayMessage("you're in assistance mode now")
            speak("you're in assistance mode now")
            time.sleep(0.5)
            eel.ShowHood()
            current_mode = "assistance"
        else:
            eel.DisplayMessage("Okay, I'm here if you need anything. Goodbye!")
            speak("Okay, I'm here if you need anything. Goodbye!")
            time.sleep(0.5)
            current_mode = "monitoring"
            eel.ExitHood()


def check_up(timeout=10):
    global current_mode
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        eel.DisplayMessage("[Listening for response...]")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            response = recognizer.recognize_google(audio).lower()
            print(f"[Heard]: {response}")
            return response
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None


def BuzzerSound():
    music_path = "www//assets//audio//buzzer.wav"
    pygame.mixer.init()
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.play()