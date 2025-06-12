import requests

url = "https://www.googleapis.com/customsearch/v1"
params = {
    "key": "AIzaSyD0K1ytAWD8HLGEr09B_Er_wsHvWzJKoGw" ,
    "cx": "b5437ecb9b3ee404c",
    "q": "Model Context Protocol MCP"
}

response = requests.get(url, params=params)
print(response.json())
