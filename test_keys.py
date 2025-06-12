import openai
import requests
import sys
from euriai import EuriaiClient
# Your API keys
EURIAI_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjNjMzMjc4NS1mZWIyLTQxNDItYTQ4YS05YWRmMjBkODhhNGMiLCJwaG9uZSI6Iis5MTg0MjE2NTY3MjAiLCJpYXQiOjE3NDA5OTY5MjMsImV4cCI6MTc3MjUzMjkyM30.T9AjeMhZ8_BE2Sy4Nap80S26M91szjvWq4HlzQUndt8"
GOOGLE_API_KEY="AIzaSyD0K1ytAWD8HLGEr09B_Er_wsHvWzJKoGw"
GOOGLE_CX="b5437ecb9b3ee404c"
SERVER_URL="http://localhost:8088"

print("=== Testing API Keys ===")

# Test 1: OpenAI API directly
print("\n1. Testing Euriai API directly...")
try:
    client = EuriaiClient(
        api_key=EURIAI_API_KEY,
        model="gpt-4.1-nano"  # or another available Euriai model
    )
    response = client.generate_completion(
        prompt="Say hello",
        temperature=0.5,
        max_tokens=10
    )
    print(f"✅ Euriai API works directly! Response: {response['choices'][0]['message']['content']}")
except Exception as e:
    print(f"❌ Euriai API error: {str(e)}")

# Test 2: Google API directly
print("\n2. Testing Google API directly...")
try:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": "test query",
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        print(f"✅ Google API works directly! Found {len(response.json().get('items', []))} results")
    else:
        print(f"❌ Google API error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Google API error: {str(e)}")

# Test 3: Server connection
print("\n3. Testing server connection...")
try:
    response = requests.get(f"{SERVER_URL}/")
    if response.status_code == 200:
        print(f"✅ Server is running! Response: {response.json()}")
    else:
        print(f"❌ Server error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Server connection error: {str(e)}")
    sys.exit("Cannot continue without server connection")

# Test 4: Debug endpoint
print("\n4. Testing server debug endpoint...")
try:
    debug_url = f"{SERVER_URL}/debug/check_keys"
    debug_data = {
        "euriai_api_key": EURIAI_API_KEY,
        "google_api_key": GOOGLE_API_KEY,
        "search_engine_id": GOOGLE_CX,
        
    }
    
    print(f"Sending keys to {debug_url}...")
    response = requests.post(debug_url, json=debug_data)
    
    if response.status_code == 200:
        print(f"✅ Debug endpoint response: {response.json()}")
    else:
        print(f"❌ Debug endpoint error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Debug endpoint error: {str(e)}")

# Test 5: Testing grading with hardcoded keys
print("\n5. Testing grade_text with hardcoded keys...")
try:
    url = f"{SERVER_URL}/tools/grade_text"
    data = {
        "text": "This is a test assignment.",
        "rubric": "Content (100%): The assignment should be a test.",
        "euriai_api_key": EURIAI_API_KEY,
        "google_api_key": GOOGLE_API_KEY,
        "search_engine_id": GOOGLE_CX
    }
    
    print(f"Euriai key length: {len(data['euriai_api_key'])}")
    print(f"Euriai key first 10 chars: {data['euriai_api_key'][:10]}...")

    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        print(f"✅ Grading works! Response: {response.json()}")
    else:
        print(f"❌ Grading error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Grading error: {str(e)}")

print("\n=== Tests completed ===")