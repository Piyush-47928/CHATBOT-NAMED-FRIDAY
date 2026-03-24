import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def chatbot(input_text):
    # Process input text
    doc = nlp(input_text)

    # Extract entities or perform other AI-related tasks here
    # For simplicity, let's just echo the input for now
    response = f"You said: {input_text}"

    return response

if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Exiting...")
            break

        response = chatbot(user_input)
        print(f"AI: {response}")

