import requests

api_key = "9k740iVfiIVyr14OS04I7RDV0fDrVO7PpG_Sya-Ywg"

url = f"https://positioning.hereapi.com/v2/locate?apikey={api_key}"
headers = {"Content-Type": "application/json"}
data = {
    "wifi": [],
    "fallback": "ip"
}

response = requests.post(url, json=data, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.text)
