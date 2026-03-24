import openai
import time

openai.api_key = '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'  # Make sure to replace 'your-api-key' with your actual API key

def ask_openai(user_input):
    try:
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=user_input,
            max_tokens=150
        )
        return response.choices[0].text.strip()

    except openai.error.RateLimitError as e:
        print(f"Rate limit exceeded. Waiting for 60 seconds.")
        time.sleep(60)
        return ask_openai(user_input)

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Example usage
user_input = input("User:")
response = ask_openai(f"You: {user_input}\nAI:")
print(response)
