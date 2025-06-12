from euriai import EuriaiClient

# Initialize the Euriai client
client = EuriaiClient(
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJjNjMzMjc4NS1mZWIyLTQxNDItYTQ4YS05YWRmMjBkODhhNGMiLCJwaG9uZSI6Iis5MTg0MjE2NTY3MjAiLCJpYXQiOjE3NDA5OTY5MjMsImV4cCI6MTc3MjUzMjkyM30.T9AjeMhZ8_BE2Sy4Nap80S26M91szjvWq4HlzQUndt8",  # Replace with your Euriai API key
    model="gpt-4.1-nano"  # or "gemini-2.5-pro-exp-03-25"
)

# Test functionpy
def test_euriai():
    try:
        response = client.generate_completion(
            prompt="Say hello world!",
            temperature=0.7,
            max_tokens=50
        )
        print("✅ Euriai Response:", response["choices"][0]["message"]["content"])
    except Exception as e:
        print("❌ Error:", e)

if __name__ == "__main__":
    test_euriai()

