import requests
import webbrowser
import re

API_KEY = "AIzaSyC2_NrrGM1Rm5zGqJEfYK0MmqHz9b_dXaY"
original_lat = 30.0444
original_lon = 31.2357

url = (
    f"https://maps.googleapis.com/maps/api/geocode/json?"
    f"latlng={original_lat},{original_lon}&language=en&region=us&key={API_KEY}"
)

response = requests.get(url)
data = response.json()

if response.status_code == 200 and data['status'] == 'OK':
    components = data['results'][0]['address_components']

    street = district = governorate = country = postal_code = ""

    for comp in components:
        if 'route' in comp['types']:
            street = comp['long_name']
        elif 'administrative_area_level_2' in comp['types']:
            district = comp['long_name']  # ← this is Qasr El Nil
        elif 'administrative_area_level_1' in comp['types']:
            governorate = comp['long_name']
        elif 'country' in comp['types']:
            country = comp['long_name']
        elif 'postal_code' in comp['types']:
            postal_code = comp['long_name']

    print(f"Location: {street}, {district}, {governorate} {postal_code}, {country}")

else:
    print(f"Error: {data.get('status')}")
    
place_name = f"{street}, {district}, {governorate} {postal_code}, {country}"


url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place_name}&language=en&region=us&key={API_KEY}"

response = requests.get(url)
data = response.json()

if response.status_code == 200 and data['status'] == 'OK':
    result = data['results'][0]
    lat = result['geometry']['location']['lat']
    lon = result['geometry']['location']['lng']
    print(f"coordinates: {lat}, {lon}")
else:
    print(f"Error: {data.get('status')}")
    
# Build the Google Maps directions URL using the lat, lon coordinates.
map_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
webbrowser.open(map_url)

import requests
import urllib.parse

spoken_destination = "Cairo University"   # Example user speech input

# Step 1: Autocomplete API
autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
params_autocomplete = {
    "input": spoken_destination,
    "key": API_KEY,
    "language": "en",
    "region": "eg"
}
resp = requests.get(autocomplete_url, params=params_autocomplete).json()
if resp["status"] != "OK" or not resp["predictions"]:
    print(f"Autocomplete failed: {resp.get('status')}")
    exit()
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
    "key": API_KEY,
    "language": "en"
}
details_resp = requests.get(details_url, params=params_details).json()

if details_resp["status"] != "OK":
    print(f"Place Details failed: {details_resp.get('status')}")
    exit()

location = details_resp["result"]["geometry"]["location"]
dest_lat = location["lat"]
dest_lon = location["lng"]

print(f"Destination coordinates: {dest_lat}, {dest_lon}")

# Step 3: Get directions with traffic and ETA
directions_url = "https://maps.googleapis.com/maps/api/directions/json"
params_directions = {
    "origin": f"{original_lat},{original_lon}",
    "destination": f"{dest_lat},{dest_lon}",
    "departure_time": "now",  # traffic-aware
    "key": API_KEY
}
directions_resp = requests.get(directions_url, params=params_directions).json()

if directions_resp["status"] != "OK":
    print(f"Directions failed: {directions_resp.get('status')}")
    exit()

route = directions_resp["routes"][0]["legs"][0]
duration = route["duration"]["text"]
duration_in_traffic = route.get("duration_in_traffic", {}).get("text", duration)
distance = route["distance"]["text"]

print(f"Estimated travel time (traffic-aware): {duration_in_traffic}")
print(f"Distance: {distance}")
steps = route['steps']
print("Step-by-step directions:")
for i, step in enumerate(steps, 1):
    # Strip HTML tags
    instruction = re.sub('<[^<]+?>', '', step['html_instructions'])
    
    # Remove Arabic characters (Unicode Arabic block: \u0600-\u06FF)
    instruction = re.sub(r'[\u0600-\u06FF]+', '', instruction)

    # Normalize spaces after stripping
    instruction = re.sub(r'\s+', ' ', instruction).strip()

    distance = step['distance']['text']
    duration = step['duration']['text']
    
    print(f"  {i}. {instruction} ({distance}, {duration})")

url = (
    f"https://api.openweathermap.org/data/2.5/weather?"
    f"lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
)

response = requests.get(url)
data = response.json()

if response.status_code == 200:
    temp = data["main"]["temp"]
    description = data["weather"][0]["description"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]

    print(f"Weather: {description.capitalize()}")
    print(f"Temperature: {temp}°C")
    print(f"Humidity: {humidity}%")
    print(f"Wind Speed: {wind_speed} m/s")
else:
    print(f"Error: {data.get('message', 'Unknown error')}")