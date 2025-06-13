# =================== MODULE IMPORTS ===================
import sys
import traceback

def my_excepthook(exctype, value, tb):
    traceback.print_exception(exctype, value, tb)
    input("Press Enter to exit...")

sys.excepthook = my_excepthook

# Core system and debugging modules
import os  # For file system access
import sys  # System-specific parameters and functions
import traceback  # To print detailed error stack traces
import numpy as np
from pydub import AudioSegment  # For audio file manipulation


# Used for playing audio files
import pygame  



# For frontend-backend interaction
import eel  

# Time-based operations
import time

# LLM interface for local models like LLaMA via Ollama
import ollama

# JSON file handling
import json

# Asynchronous I/O support
import asyncio

# Offline TTS engine from Microsoft Edge voices
import edge_tts

# For current date/time
from datetime import datetime

# For IP-based location lookup
import geocoder  

# Open URLs in browser
import webbrowser

# Location services and reverse geocoding

from geopy.geocoders import Nominatim


# HTTP requests (used by some backend functions)
import requests


from send_email import send_alert_email  # Custom module to send alert email

# Configuration variables like WhatsApp contacts
from config import *  

from groq import Groq
import re
import urllib.parse


# =================== APP STATE ===================



class AppState:
    """
    Holds the global state of the assistant application.
    """
    def __init__(self):
        self.current_mode = "monitoring"  # Tracks if assistant is monitoring or assisting
        self.mic_pressed = False  # Flag to indicate mic button was pressed
        self.conversation_history = []  # Stores LLM conversation context
        self.location_override = None  # Holds GPS location from frontend if available
        self.json_file_path = "data\driver_assistant.json"  # Path to monitoring data
        self.json_flag = True
        self.speak_flag=True


# =================== AUDIO MANAGER ===================

class AudioManager:
    """
    Manages audio output, including TTS, buzzer alarms, and music playback.
    """

    def __init__(self):
        self.state = state  # Use the shared app state
        pygame.mixer.init()  # Initialize the Pygame mixer for audio playback
    
    def play(self, path):
        """
        Play an audio file from the given path.
        """
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

    def stop(self):
        """
        Stop any currently playing audio.
        """
        pygame.mixer.music.stop()

    def pause(self):
        """
        Pause the current audio.
        """
        pygame.mixer.music.pause()

    def unpause(self):
        """
        Resume paused audio.
        """
        pygame.mixer.music.unpause()

    def set_volume(self, volume):
        """
        Set the audio volume (0.0 to 1.0).
        """
        pygame.mixer.music.set_volume(volume)
    
    @eel.expose
    def speak(self, text):
        """
        Speak a given text using edge TTS.
        """
        print(f"[TTS] Speaking: {text}")
        asyncio.run(self.edge_speak(text))  # Run the async function synchronously

    async def edge_speak(self, text, voice="en-US-AriaNeural"):
        """
        Convert text to speech using edge-tts and play it with pygame.
        """
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            mp3_bytes = b""  # Buffer for raw audio

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_bytes += chunk["data"]

            # Use project's temp_audio directory
            temp_dir = os.path.join(os.getcwd(), "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a unique filename
            temp_file = os.path.join(temp_dir, f"temp_audio_{int(time.time())}.mp3")
            
            # Save the audio to a file
            with open(temp_file, "wb") as f:
                f.write(mp3_bytes)
            
            # Play the audio using pygame
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # Wait for the audio to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Stop and unload the music
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            
            # Clean up the temporary file
            # try:
            #     #os.remove(temp_file)
            # except Exception as e:
            #     print(f"[WARNING] Could not remove temp file: {e}")

        except Exception as e:
            print(f"[ERROR] Text-to-speech failed: {e}")
            # Try to play a fallback sound if available
            try:
                pygame.mixer.music.load("www/assets/audio/buzzer.wav")
                pygame.mixer.music.play()
            except:
                pass

    def BuzzerSound(self):
        """
        Play a buzzer alert sound.
        """
        music_path = "www//assets//audio//buzzer.wav"
        self.play(music_path)

        
class LLMManager():
    """
    Handles conversation flow with the user and communicates with the LLM (LLaMA via Ollama).
    """

    def __init__(self, state, Audio, User):
        self.state = state  # Shared app state
        self.User = User  # Handles STT
        self.Audio = Audio  # Handles TTS and audio output

        # Initialize conversation history with system prompt
        self.state.conversation_history = [self.generate_initial_context()]
        self.api_key = "9k740iVfiIVyrl40S04I7RDV0ffDrVO7PpG_Sya-Ywg"  # HERE API key
        
    def generate_initial_context(self):
        """
        Generates the system prompt with time, date, and location for assistant initialization.
        """
        now = datetime.now()
        current_date = now.strftime("%A, %B %d, %Y")
        current_time = now.strftime("%I:%M %p")

        try:
            # Approximate location via IP
            g = geocoder.ip('me')
            city = g.city or "an unknown city"
            country = g.country or "an unknown country"
            location_text = f"You are currently in {city}, {country}."

            # Override location from frontend if available
            if self.state.location_override:
                location_text = f"You are currently at {self.state.location_override}."
        except Exception as e:
            location_text = "Location is unavailable."
            print(f"[ERROR] Failed to get location: {e}")

        # System message that defines the assistant's role
        system_prompt = f"""You are a helpful driving assistant.
Today is {current_date} and the time is {current_time}.
{location_text}
You do functions like providing him current location, current time, traffic and weather info, estimated arrival time to destinations and routing steps to these destinations.
You also talk with him if he feels sleepy or suffers fatigue.
Only respond in 1–2 sentences unless instructed otherwise.
"""

        return {"role": "system", "content": system_prompt}

    def estimate_tokens(self, text):
        """
        Estimates the number of tokens in a string (approx 1.3 tokens per word).
        """
        return len(text.split()) * 1.3

    def trim_history(self, history, max_tokens=7000):
        """
        Keeps conversation within token limits by trimming older messages, retaining the system prompt.
        """
        total_tokens = 0
        trimmed = []

        # Retain the initial system message
        if history and history[0]['role'] == 'system':
            trimmed.append(history[0])
            history = history[1:]

        # Keep the most recent messages up to the token limit
        for msg in reversed(history):
            tokens = self.estimate_tokens(msg['content'])
            if total_tokens + tokens <= max_tokens:
                trimmed.insert(1, msg)  # Insert after system message
                total_tokens += tokens
            else:
                break  # Stop adding if we hit the token limit

        return trimmed

    def classify_user_intent(self, query):
        intent_prompt = f"""
        You are a classification engine. Do not explain or speak.
        You're a part of driver assistance that helps drivers in Cairo, Egypt.

        ONLY return a valid JSON object with these ONLY 2 elements:
        - type: one of ["chat", "weather", "traffic", "eta", "navigate"]
        - destination: like "Giza" or "Sheikh Zayed" or "the drive Nasr City" and if the driver means his current location make it empty like ""

        Destinations can be precise like "Sheikh Zayed st.34" or "Sheikh Zayed district 5" or "Mesaha square in dokki".
        If the driver means his current location, make the type chat and destination empty like "".
        
        Examples:
        User: "what's the weather like in Giza?"
        → {{ "type": "weather", "destination": "Giza" }}

        User: "how's traffic near me?"
        → {{ "type": "traffic" }}

        User: "how far is Sheikh Zayed?"
        → {{ "type": "eta", "destination": "Sheikh Zayed" }}

        User: "navigate to maadi"
        → {{ "type": "navigate", "destination": "maadi" }}
        
        User: "navigate to waterway New Cairo"
        → {{ "type": "navigate", "destination": "waterway New Cairo" }}

        User: "tell me a joke"
        → {{ "type": "chat" }}

        Now classify this input:
        "{query}"
        Respond ONLY with JSON. No explanation.

        """

        try:
            response = ollama.chat(model="llama3.2", messages=[
                { "role": "user", "content": intent_prompt }
            ])
            intent_json = json.loads(response['message']['content'])
            return intent_json
        except Exception as e:
            print("[ERROR] Intent classification failed:", e)
            return { "type": "chat" }  # Fallback

    @eel.expose
    def PassToLlm(self):
        """
        Called when assistant is in 'assistance' mode to handle user queries and reply via LLM.
        """
        silence_timeout = 30  # Timeout to return to monitoring mode if user is silent
        last_response_time = time.time()

        while self.state.current_mode == "assistance":
            query = self.User.takecommand()  # Get speech input
            print(f"[USER]: {query}")

            # If no speech detected
            if query == "" :
                if time.time() - last_response_time > silence_timeout:
                    eel.DisplayMessage("No response detected. Going back to monitoring mode.")
                    self.Audio.speak("No response detected. Going back to monitoring mode.")
                    self.state.current_mode = "monitoring"
                    self.state.mic_pressed = False
                    eel.ExitHood()
                    break
                continue  # Keep trying if still within timeout

            # Reset silence timer
            last_response_time = time.time()

            # Add user message to conversation
            user_message = {"role": "user", "content": query}
            self.state.conversation_history.append(user_message)



            #----------------------------Check for close gps phrases---------------------------------------
            if any(phrase in query for phrase in ["close gps", "stop gps", "turn off gps", "hide","hide gps","close map","stop map"]):
                print("[DEBUG] closing google maps website returning to assistant home screen.")
                eel.DisplayMessage("Got it!")
                self.Audio.speak("Got it!")
                eel.DisplayMessage("Closing maps.")
                self.Audio.speak("Closing maps.")
                # Close maps or stop GPS tracking
                from engine.features import CloseMaps
                CloseMaps()
                self.state.current_mode = "monitoring"
                self.state.mic_pressed = False
                eel.ExitHood()
                eel.DisplayMessage("")
                break

            # Check for open gps phrases
            if any(phrase in query for phrase in ["open gps", "turn on gps", "open maps","open"]):
                print("[DEBUG] opening google maps website.")
                from engine.features import OpenGps
                eel.DisplayMessage("Got it!")
                self.Audio.speak("Got it!")
                eel.DisplayMessage("Opening maps.")
                self.Audio.speak("Opening maps.")
                OpenGps("gps")
                self.state.current_mode = "monitoring"
                self.state.mic_pressed = False
                eel.ExitHood()
                eel.DisplayMessage("")
                break

            # ======================== Exit Phrases ============================
            if any(phrase in query for phrase in ["goodbye", "bye", "thank you", "thanks", "exit", "end", "close"]):
                print("[DEBUG] Switching to monitoring mode and ending chatting.")
                eel.DisplayMessage("Goodbye driver.")
                self.Audio.speak("Goodbye driver.")
                self.state.current_mode = "monitoring"
                self.state.mic_pressed = False
                eel.ExitHood()
                eel.DisplayMessage("")
                break

            # =================== enable Monitoring ==========================
            if any(phrase in query for phrase in ["enable monitoring", "monitoring mode", "back to monitoring", "start monitoring", "start monitor", "enable"]):
                print("[DEBUG] Switching again to monitoring mode.")
                eel.DisplayMessage("Got it!")
                self.Audio.speak("Got it!")
                eel.DisplayMessage("Switching to monitoring mode.")
                self.Audio.speak("Switching to monitoring mode.")
                self.state.current_mode = "monitoring"
                self.state.mic_pressed = False
                self.state.speak_flag=True
                self.state.json_flag=True
                print(f"[DEBUG] speak flag: {self.state.speak_flag}")
                eel.ExitHood()
                eel.DisplayMessage("")
                break


            # =================== disable Monitoring ==========================
            if any(phrase in query for phrase in ["disable monitoring", "off monitoring", "end monitoring", "disable"]):
                print("[DEBUG] Switching again to idle mode.") 
                eel.DisplayMessage("Got it!")
                self.Audio.speak("Got it!")
                eel.DisplayMessage("Monitoring is disabled but it is good feature for your safety if you want to re-enable it just tell me")
                self.Audio.speak("Monitoring is disabled but it is good feature for your safety if you want to re-enable it just tell me ")
                self.state.current_mode = "monitoring"
                self.state.mic_pressed = False
                self.state.speak_flag=False
                print(f"[DEBUG] speak flag: {self.state.speak_flag}")
                #eel.updateMonitorBtnSpeak(False)
                self.state.json_flag=False
                eel.ExitHood()
                eel.DisplayMessage("")
                break

            # =================== chat or call with someone ==========================
            if any(phrase in query for phrase in ["send", "text", "message", "whatsapp", "call", "voice call", "make a call", "ring"]):
                self.state.current_mode = "assistance"
                is_call = any(word in query for word in ["call", "voice call", "make a call", "ring"])
                action_type = "call" if is_call else "message"

                # Contact dictionary
                contacts = {
                    "nada": "+201093661321",
                    "mama": "+201270509918",
                    # Add more contacts here
                }

                # Attempt to get name from query
                name = None
                for contact_name in contacts:
                    if contact_name in query:
                        name = contact_name
                        break

                # If name not found, ask once more
                if name is None:
                    self.Audio.speak("sorry i didnt catch the name can you repeat it")
                    name_attempt = self.User.takecommand()
                    for contact_name in contacts:
                        if contact_name in name_attempt:
                            name = contact_name
                            break

                    if name is None:
                        self.Audio.speak("I still can't catch the name...leaving")
                        return  # Exit this section

                number = contacts[name]
                from engine.features import send_whatsApp_msg

                # === CALL HANDLING ===
                if action_type == "call":
                    self.Audio.speak(f"Calling {name} on WhatsApp.")
                    send_whatsApp_msg(number, message="", flag="call", name=name)
                    continue

                # === MESSAGE HANDLING ===
                else:
                    eel.DisplayMessage(f"Got it. Now tell me the message to send to {name}.")
                    self.Audio.speak(f"Got it. Now tell me the message to send to {name}.")

                    message = "none"
                    start_time = time.time()
                    timeout = 25  # seconds
                    retry_prompt_given = False

                    while message == "none" and (time.time() - start_time) < timeout:
                        message = self.User.takecommand()

                        if message == "none" and not retry_prompt_given:
                            self.Audio.speak("Please say it again.")
                            retry_prompt_given = True

                    if message == "none":
                        self.Audio.speak("No message received...leaving .")
                        return  # Exit this section

                    send_whatsApp_msg(number, message, flag="message", name=name)
                    self.Audio.speak("Message sent.")
                    continue

        
            # =================== Weather or Navigation based on Keywords ==========================
            intent = self.classify_user_intent(query)
            intent_type = intent.get("type")
            destination = intent.get("destination")
            
            print(f"[DEBUG] Intent type: {intent_type}")
            print(f"[DEBUG] Destination: {destination}")
                    
            if intent_type in ["eta", "traffic"]:

                dest_lat, dest_lon = self.geocode_destination(destination)
                with open("location.json", "r") as f:
                    loc = json.load(f)
                    origin_lat = loc["latitude"]
                    origin_lon = loc["longitude"]

                route_response = self.get_route_info(origin_lat, origin_lon, dest_lat, dest_lon)
                eel.DisplayMessage(route_response)
                self.Audio.speak(route_response)
                continue

            elif intent_type == "navigate":
                self.handle_navigation(destination)
                continue

            elif intent_type == "chat":
            # === Step 3: If general chat, respond and update context ===
                user_msg = { "role": "user", "content": query }
                self.state.conversation_history.append(user_msg)

                try:
                    trimmed_history = self.trim_history(self.state.conversation_history)
                    chat_response = ollama.chat(model="llama3.2", messages=trimmed_history)
                    reply = chat_response["message"]["content"]

                    eel.DisplayMessage(reply)
                    self.Audio.speak(reply)
                    assistant_msg = { "role": "assistant", "content": reply }
                    self.state.conversation_history.append(assistant_msg)

                except (requests.exceptions.RequestException, KeyError, ValueError, TypeError) as e:
                    print(f"[ERROR] LLM call failed: {e}")
                    eel.DisplayMessage("Sorry, I couldn't process that.")
                    self.Audio.speak("Sorry, I couldn't process that.")
                continue
            
            elif intent_type == "weather":
                try:
                    if destination:
                        lat, lon = self.geocode_destination(destination)
                    else:
                        with open("location.json", "r") as f:
                            loc = json.load(f)
                            lat = loc["latitude"]
                            lon = loc["longitude"]

                    weather = self.get_weather(lat=lat, lon=lon)
                    eel.DisplayMessage(weather)
                    self.Audio.speak(weather)
                except (requests.exceptions.RequestException, KeyError, ValueError) as e:
                    print("[ERROR] Weather handling failed:", e)
                    self.Audio.speak("Sorry, I couldn't fetch the weather right now.")
                continue


                
    def geocode_destination(self, destination):
        # Step 1: Autocomplete API
        autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params_autocomplete = {
            "input": destination,
            "key": GOOGLE_MAPS_API_KEY,
            "language": "en",
            "region": "eg"
        }
        resp = requests.get(autocomplete_url, params=params_autocomplete, timeout=5).json()
        if resp["status"] != "OK" or not resp["predictions"]:
            print(f"Autocomplete failed: {resp.get('status')}")
            self.Audio.speak("Sorry I couldn't hear you clearly, can you repeat again")
            self.PassToLlm()
        raw_description = resp['predictions'][0]['description']

        # 1. Remove all non-ASCII characters (Arabic, emoji, etc.)
        ascii_only = re.sub(r'[^\x00-\x7F]+', '', raw_description)

        # 2. Replace multiple commas/whitespace with a single comma + space
        clean_description = re.sub(r'\s*,\s*', ', ', ascii_only)        # Normalize commas
        clean_description = re.sub(r'(,\s*)+', ', ', clean_description) # Collapse repeated commas
        clean_description = re.sub(r'\s+', ' ', clean_description).strip() # Final whitespace cleanup

        print(f"Top match: {clean_description}")
        place_id = resp["predictions"][0]["place_id"]


        # Step 2: Place Details → Get lat/lon
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        params_details = {
            "place_id": place_id,
            "key": GOOGLE_MAPS_API_KEY,
            "language": "en"
        }
        details_resp = requests.get(details_url, params=params_details, timeout=5).json()

        if details_resp["status"] != "OK":
            print(f"Place Details failed: {details_resp.get('status')}")
            exit()

        location = details_resp["result"]["geometry"]["location"]
        dest_lat = location["lat"]
        dest_lon = location["lng"]

        print(f"Destination coordinates: {dest_lat}, {dest_lon}")
        return dest_lat, dest_lon



    def handle_navigation(self, destination):
        print(f"[DEBUG] Handling navigation to: {destination}")
        # Step 1: Autocomplete API
        autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params_autocomplete = {
            "input": destination,
            "key": GOOGLE_MAPS_API_KEY,
            "language": "en",
            "region": "eg"
        }
        resp = requests.get(autocomplete_url, params=params_autocomplete, timeout=5).json()
        if resp["status"] != "OK" or not resp["predictions"]:
            print(f"Autocomplete failed: {resp.get('status')}")
            self.Audio.speak("Sorry I couldn't hear you clearly, can you repeat again")
            self.PassToLlm()

        raw_description = resp['predictions'][0]['description']

        # 1. Remove all non-ASCII characters (Arabic, emoji, etc.)
        ascii_only = re.sub(r'[^\x00-\x7F]+', '', raw_description)

        # 2. Replace multiple commas/whitespace with a single comma + space
        clean_description = re.sub(r'\s*,\s*', ', ', ascii_only)        # Normalize commas
        clean_description = re.sub(r'(,\s*)+', ', ', clean_description) # Collapse repeated commas
        clean_description = re.sub(r'\s+', ' ', clean_description).strip() # Final whitespace cleanup
        print(f"Top match: {clean_description}")
        # Extract the destination string from the user's query.
        if clean_description:
            eel.DisplayMessage(f"Opening directions to {clean_description.title()}...")
            self.Audio.speak(f"Opening directions to {clean_description.title()}...")
            
            # Get the destination's latitude and longitude via HERE Geocoding API.
            dest_lat, dest_lon = self.geocode_destination(destination)
            if dest_lat is None or dest_lon is None:
                self.Audio.speak("Sorry, I couldn't find that location.")
                return
            
            # Build the Google Maps directions URL using the lat, lon coordinates.
            map_url = f"https://www.google.com/maps/dir/?api=1&destination={dest_lat},{dest_lon}"
            webbrowser.open(map_url)
        else:
            self.Audio.speak("Where would you like to go?")

    def get_route_info(self, origin_lat, origin_lon, dest_lat, dest_lon):
        if not all([origin_lat, origin_lon, dest_lat, dest_lon]):
            print("[ERROR] Invalid coordinates provided.")
            return "Location data is incomplete."

        directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        params_directions = {
            "origin": f"{origin_lat},{origin_lon}",
            "destination": f"{dest_lat},{dest_lon}",
            "departure_time": "now",
            "key": GOOGLE_MAPS_API_KEY
        }

        directions_resp = requests.get(directions_url, params=params_directions, timeout=5).json()

        if directions_resp["status"] != "OK":
            print(f"Directions failed: {directions_resp.get('status')}")
            return "Could not retrieve directions."

        route = directions_resp["routes"][0]["legs"][0]
        duration = route["duration"]["text"]
        duration_sec = route["duration"]["value"]
        traffic_sec = route.get("duration_in_traffic", {}).get("value", duration_sec)
        duration_in_traffic = route.get("duration_in_traffic", {}).get("text", duration)
        distance = route["distance"]["text"]

        # Start accumulating output
        output = []
        output.append(f"Estimated travel time is {duration_in_traffic}, covering a distance of {distance}.")

        # Add traffic delay if exists
        delay_sec = traffic_sec - duration_sec
        if delay_sec > 60:
            delay_min = round(delay_sec / 60)
            output.append(f"Note: Expect a delay of approximately {delay_min} minute{'s' if delay_min > 1 else ''} due to traffic.")

        # Step-by-step breakdown
        steps = route['steps']
        output.append("Here are the main steps:")

        for i, step in enumerate(steps, 1):
            instruction = re.sub('<[^<]+?>', '', step['html_instructions'])
            instruction = re.sub(r'[\u0600-\u06FF]+', '', instruction)
            instruction = re.sub(r'\s+', ' ', instruction).strip()
            step_distance = step['distance']['text']
            step_duration = step['duration']['text']
            output.append(f"{i}. {instruction} ({step_distance}, {step_duration})")

        # Full route response to summarize
        route_response = " ".join(output)

        # Prepare LLM summarization prompt
        user_msg = {
            "role": "user",
            "content": f"Summarize this driving route steps in 3 to 4 short while keeping the highlighted info like the Estimated travel time and the distance covered, clear sentences for speaking out loud:\n{route_response}"
        }
        self.state.conversation_history.append(user_msg)

        try:
            trimmed_history = self.trim_history(self.state.conversation_history)
            chat_response = ollama.chat(model="llama3.2", messages=trimmed_history)
            reply = chat_response["message"]["content"]

            assistant_msg = { "role": "assistant", "content": reply }
            self.state.conversation_history.append(assistant_msg)
            route_response = reply  # Replace full text with summarized version
        except (requests.exceptions.RequestException, KeyError, ValueError, TypeError) as e:
            print(f"[LLM ERROR] Could not summarize route: {e}")
            # Use the full response if LLM fails

        return route_response


        
    def get_weather(self, lat=None, lon=None, location_name=None):
        """
        Fetches current weather from OpenWeather API by coordinates or location name.
        """
        OPENWEATHER_API_KEY = "0eb49539ccd61afc3946866765e1d42e"  # OPENWEATHER_API_KEY

        if lat and lon:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        elif location_name:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={location_name}&appid={OPENWEATHER_API_KEY}&units=metric"
        else:
            return "Location for weather not provided."

        try:
            response = requests.get(url)
            data = response.json()

            if data.get("cod") != 200:
                print(f"[ERROR] Weather API error: {data.get('message')}")
                return "Sorry, I couldn't fetch the weather data."

            description = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            city = data["name"]

            weather_report = (
                f"Current weather in provided destination is {description}. "
                f"Temperature is {temp}°C, feels like {feels_like}°C. "
                f"Humidity is {humidity}%."
            )
            return weather_report

        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            print("[ERROR] Weather API call failed:", e)
            return "Weather data is currently unavailable."

class UserManager:
    def __init__(self, state, Audio):
        self.state = state  # Reference to global app state
        self.Audio = Audio  # Reference to AudioManager for playing voice responses
        self.client = Groq(api_key=GROQ_API_KEY) # Groq API key
        
        
    def record_audio(self, duration=6, sample_rate=16000, file_path="input.wav"):
        import sounddevice as sd
        from scipy.io.wavfile import write

        print("[🎙️] Recording audio...")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        write(file_path, sample_rate, audio)
        print(f"[✅] Audio saved to {file_path}")
        return file_path
    
    def is_audio_silent(self, filepath, threshold_db=-40.0):
        audio = AudioSegment.from_file(filepath)
        return audio.dBFS < threshold_db  # dBFS = decibels relative to full scale
    
    def transcribe_audio_with_groq(self, file_path, lang="en"):
        
        prompt = (
    "You are transcribing short English voice commands from a driver assistant system in Egypt. "
    "Expect navigation-related words like 'navigate to', 'how far is', and 'estimated arrival time'. "
    "Egyptian area names may include: Zahraa El Maadi, Maadi, Nasr City, Dokki, Mohandessin, Giza, Zamalek, Sheraton, New Cairo, El Rehab, Shorouk, 6 October, "
    "Giza Pyramids, Sheikh Zayed, Heliopolis, Downtown Cairo, Cairo Airport, Mokattam, Garden City, Manial, Abbasia, Ramses, Sayeda Zeinab, Helwan, Ain Shams, "
    "Hadayek El Maadi, El Marg, El Obour, El Salam, El Basatin, El Tagamoa, Fifth Settlement, Sixth Settlement, Masr El Gedida, Badr City, El Manyal, El Matareya, "
    "El Waily, El Darassa, El Mokattam, Tora, Zahraa Nasr City, Gesr El Suez, New Capital, El Talbia, Warraq, Kerdasa, Boulaq, Faisal Street, Haram, Imbaba, "
    "Rod El Farag, El Zawya El Hamra, El Sayeda Aisha, and El Mohandessin. ")



        try:
            
            # 🔍 Check if the file is actually silent
            if self.is_audio_silent(file_path):
                print("[⚠️] Skipping transcription: audio is silent or low energy.")
                return ""

            with open(file_path, "rb") as file:
                result = self.client.audio.transcriptions.create(
                    file=file,
                    model="whisper-large-v3",
                    language=lang,
                    response_format="text",
                    temperature=0.2,
                    prompt=prompt,
                )
            return result.strip().lower()
        except Exception as e:
            print(f"[❌] Whisper API error: {e}")
            return "none"
        finally:
            # Automatically delete audio file
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[🗑️] Deleted {file_path}")

    @eel.expose
    def takecommand(self, timeout=15, phrase_time_limit=7, lang="en"):
        """
        Listens to the user's voice and converts it to text.
        Returns recognized text in lowercase, or 'none' if failed.
        """

        try:
            print("[🎙️] Listening for command...")
            eel.DisplayMessage("[Listening for command...]")
            file_path = self.record_audio(duration=phrase_time_limit)
            print("[Recognizing...]")
            eel.DisplayMessage("[Recognizing...]")
            recognized_text = self.transcribe_audio_with_groq(file_path, lang=lang)
            print(f"[STT] You said: {recognized_text}")
            return recognized_text
        except Exception as e:
            print("[ERROR] takecommand failed:", e)
            return "none"

    @eel.expose
    def ListenForWakeWord(self, phrase_time_limit=5, wake_word="hey nova"):
        """
        Listens for a specific wake word. If detected, returns True.
        Otherwise, returns False.
        """

        print("[Listening for wake word...]")
        file_path = self.record_audio(duration=phrase_time_limit)
        print("[Recognizing...]")
        recognized_text = self.transcribe_audio_with_groq(file_path, lang="en")
        print(f"[STT] You said: {recognized_text}")


        if wake_word in recognized_text:
            # Wake word matched
            eel.DisplayMessage("Hey driver, how can I help you?")
            self.Audio.speak("Hey driver, how can I help you?")
            time.sleep(0.5)
            return True
            


    def send_feedback_to_EC(self):
        """
        Notifies emergency contact by email and WhatsApp if driver is unresponsive.
        """
        send_alert_email(LIVE_STREAM_URL, RECEIVER_EMAIL)  # Send email with livestream link

        from engine.features import send_whatsApp_msg
        # Send WhatsApp message
        send_whatsApp_msg(
            EMERGENCY_CONTACT_NUMBER,
            "🚨 *Emergency Alert!* 🚨\nDriver seems to be unresponsive 😔\n📺 Check the live stream here:\n🔗 " + LIVE_STREAM_URL,
            'message',
            EMERGENCY_CONTACT_NAME
        )

        time.sleep(1)  # Wait briefly

        # Trigger WhatsApp call
        send_whatsApp_msg(
            EMERGENCY_CONTACT_NUMBER,
            "",
            'call',
            EMERGENCY_CONTACT_NAME
        )

    def alert(self):
        """
        Triggered by fatigue detection. Asks driver if they're okay.
        If no response, sends emergency alert.
        """
        self.state.current_mode = "sleep_alert"
        eel.DisplayMessage("Are you okay? Can you hear me?")
        self.Audio.speak("Are you okay? Can you hear me?")
        time.sleep(0.5)
        eel.ShowHood()

        # Wait for response
        response = self.check_up(timeout=10)

        if response is None:
            # No response — alert emergency contact
            eel.DisplayMessage("Dangerous! No response from driver.")
            self.Audio.speak("Dangerous! No response from driver.")
            time.sleep(0.5)
            self.Audio.BuzzerSound()
            time.sleep(0.5)
            self.send_feedback_to_EC()
            time.sleep(7)
            self.state.current_mode = "monitoring"
            eel.ExitHood()
            return

        else:
            # Driver responded — ask if they want to talk
            eel.DisplayMessage("Do you want to talk to me?")
            self.Audio.speak("Do you want to talk to me?")
            time.sleep(0.5)
            answer = self.check_up(timeout=10)

            if answer and "yes" in answer:
                eel.DisplayMessage("Okay, I'm here to help you , you're in assistance mode now")
                self.Audio.speak("Okay, I'm here to help you , you're in assistance mode now")
                time.sleep(0.5)
                eel.ShowHood()
                self.state.current_mode = "assistance"
            else:
                eel.DisplayMessage("okay, let me know if you need me")
                self.Audio.speak("okay, let me know if you need me")
                time.sleep(0.5)
                self.state.current_mode = "monitoring"
                eel.ExitHood()

    def check_up(self, timeout=10, lang="en"):
        """
        Listen for any response from the user within the timeout.
        """
        try:
            print("[Listening for response...]")
            eel.DisplayMessage("[Listening for response...]")
            
            # Reuse existing audio recording
            file_path = self.record_audio(duration=timeout, file_path="response.wav")
            
            # Reuse existing Groq transcription
            response = self.transcribe_audio_with_groq(file_path, lang=lang)
            
            if response:
                print(f"[Heard]: {response}")
                return response
            else:
                print("[WARN] No valid response heard.")
                return None

        except Exception as e:
            print(f"[❌] check_up error: {e}")
            return None


            
# Create instances of main classes
state = AppState()
Audio = AudioManager()
User = UserManager(state, Audio)
LLM = LLMManager(state, Audio, User)

@eel.expose
def ReceiveLocation(lat, lon):
    """
    Receives latitude and longitude from frontend and reverse geocodes it using geopy.Nominatim.
    Saves full location info into a JSON file and updates assistant context.
    """
    try:
        geolocator = Nominatim(user_agent="driver_assistant")
        location = geolocator.reverse((lat, lon), language="en")
        address = location.address

        # Save to location.json
        with open("location.json", "w") as f:
            json.dump({
                "latitude": lat,
                "longitude": lon,
                "address": address
            }, f)

        print(f"[📍] Precise location: {address}")
        state.location_override = address

        # Update the system prompt in conversation history
        if state.conversation_history and state.conversation_history[0]["role"] == "system":
            state.conversation_history[0] = LLM.generate_initial_context()
        else:
            print("[WARN] Couldn't update system message — history not ready.")

    except Exception as e:
        print(f"[ERROR] Failed to reverse geocode: {e}")


@eel.expose
def set_mic_pressed():
    """
    Marks mic as pressed from frontend event.
    """
    state.mic_pressed = True

# this is for disable and enable manually
@eel.expose
def Set_jason_flag():
    state.json_flag = True
    state.speak_flag=True
    Audio.speak("Monitoring is enabled.")
    
@eel.expose
def Clear_jason_flag():
    state.json_flag = False
    Audio.speak("Monitoring is disabled.")

@eel.expose
def get_monitor_mode():
    return "on" if state.json_flag else "off"

def fetch_json_file():
    """
    Fetches the driver alert JSON file from a remote server.
    """
    try:
        url = "https://dmslivestreaming.ngrok.io/driver_assistant.json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        # Save to local file
        with open(state.json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("[INFO] JSON file fetched and saved.")
    except Exception as e:
        print(f"[ERROR] Failed to fetch JSON file: {e}")


import time

def safe_remove_file(filepath, retries=5, delay=0.5):
    for _ in range(retries):
        try:
            os.remove(filepath)
            print(f"[INFO] Successfully deleted {filepath}")
            return
        except PermissionError:
            print(f"[WARN] File is busy. Retrying in {delay} sec...")
            time.sleep(delay)
    print(f"[ERROR] Failed to delete {filepath} after {retries} attempts.")

@eel.expose
def monitoring_loop():
    """
    Background loop that runs in the monitoring mode:
    - Checks driver alert JSON for fatigue or distraction
    - Detects wake word or mic press
    - Sends data to LLM for safety suggestions if necessary
    """
    while True:
        data = {}  # Initialize with empty dict in case fetch fails

        # # Fetch the driver alert JSON file
        # fetch_json_file()

        # # Load the driver alert JSON if it exists
        # if os.path.exists(state.json_file_path):
        #     try:
        #         # Open and read the file
        #         with open(state.json_file_path, "r") as f:
        #             data = json.load(f)  # After this, file auto-closes


        #     except Exception as e:
        #         print(f"[ERROR] Could not load or delete JSON file: {e}")


        # # If driver is sleepy or fatigued → trigger alert flow
        # if data.get("sleep_alert", "").lower() == "on":
        #     state.current_mode = "sleep_Alert" 
        #     User.alert()  # Trigger alert dialog
        #     time.sleep(5)
        #     continue


        # If mic was pressed or wake word heard while monitoring → switch to assistance mode
        if state.mic_pressed or (state.current_mode == "monitoring" and User.ListenForWakeWord()):
            eel.DisplayMessage("")
            state.current_mode = "assistance"
            eel.ShowHood()  # Show assistant UI
            LLM.PassToLlm()  # Start listening to driver
            continue

        # If still in assistance mode (after wake word), continue handling conversation
        if state.current_mode == "assistance":
            eel.ShowHood()
            LLM.PassToLlm()
            continue


        
        if state.current_mode == "monitoring" and not state.mic_pressed and (state.json_flag and state.speak_flag):
            print(f"[DEBUG] json flag: {state.json_flag}")
            print(f"[DEBUG] speak flag: {state.speak_flag}")

            # Fetch the driver alert JSON file
            fetch_json_file()
            # Re-read the JSON to get the most updated status
            # if os.path.exists(state.json_file_path):
            #     with open(state.json_file_path, "r") as f:
            #         data = json.load(f)

            #         #os.remove(state.json_file_path)  # Delete the file after reading 

            #         # If user mode changed mid-read, stop
            #         if state.current_mode != "monitoring":
            #             continue

            #         # Parse the alerts into lowercase strings
            #         fatigue = data.get("Fatigue_Alert", "").lower()
            #         distraction = data.get("Distraction_Alert", "").lower()
            #         action = data.get("Activity_Alert", "").lower()
            #         hands = data.get("HOW_Alert", "").lower()

            #         # Still double-check mode and mic again before proceeding
            #         if state.current_mode == "monitoring" and not state.mic_pressed:
            #             if state.current_mode != "monitoring":
            #                 continue

            #             # If all is good — safe driving detected — do nothing
            #             if action == "safe driving" and distraction == "off" and hands == "hands on wheel" and fatigue == "off":
            #                 continue

            #             # Otherwise, send a summarized prompt to LLM for polite safety tip
            #             prompt = (
            #                 f"Driver activity: {action}. "
            #                 f"Distraction alert: {distraction}. "
            #                 f"Hands on or off wheel: {hands}. "
            #                 f"Fatigue alert: {fatigue}. "
            #                 f"Based on these observations, provide a short, polite safety instruction in 20 words or less. "
            #                 f"The tone should be clear and supportive. Avoid generic advice."
            #             )

            #             try:
            #                 # Wrap it as a user message for LLM
            #                 safe_history = [{"role": "user", "content": prompt}]
            #                 response = ollama.chat(model='llama3.2', messages=safe_history)
            #                 reply = response['message']['content']

            #                 print(f"[LLM] Assistant response: {reply}")
            #                 # eel.DisplayMessage(reply)  # Show on frontend
            #                 Audio.speak(reply)         # Say it aloud

            #             except Exception as e:
            #                 # Catch LLM issues
            #                 print(f"[ERROR] LLM failed during monitoring: {e}")
            #                 eel.DisplayMessage("Error analyzing driver alert data.")
            #                 Audio.speak("Error analyzing driver alert data.")
        else:
            print(" ehna fl else")
            print(f"[DEBUG] json flag: {state.json_flag}")
            print(f"[DEBUG] speak flag: {state.speak_flag}")
            continue

        # Wait a short time before next loop
        time.sleep(0.1)
