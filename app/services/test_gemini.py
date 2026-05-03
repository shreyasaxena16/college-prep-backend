from google import genai

client = genai.Client(api_key="AIzaSyB2dpT-jH8KuL5cZVdC5JzpThpboWIrZE0")

response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="Say hello in one word"
)

print(response.text)