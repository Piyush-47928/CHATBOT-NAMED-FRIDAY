from openai import OpenAI
import os
import pygame
import datetime
from datetime import date
from datetime import datetime


# Set your OpenAI API key as an environment variable
api_key = 'YOUR API KEY'
os.environ["OPENAI_API_KEY"] = api_key

#MEMORY HOUSE
user_conversation = [{"role": "system", "content": "Your name is Friday and you are a human like robot whose work is to communicate with humans. You can remember names."}]

today_date = date.today()
formatted_date = today_date.strftime("%Y-%m-%d")

date = f"Todays date is {formatted_date}"
memory_date = dict(role="system",content=date)
user_conversation.append(memory_date)




current_time = datetime.now().strftime("%H:%M:%S")
time = f"Todays time is {current_time}"
memory_time = dict(role="system",content=time)
user_conversation.append(memory_time)






client = OpenAI()

'''


'''




#LOOP
while True:
      import speech_recognition as sr
      import pyaudio
      import wave

      def record_audio(filename, sample_rate=44100, chunk_size=1024):
          """
          Record audio from the microphone and save it to a WAV file.

          Parameters:
          - filename: The name of the WAV file to save the recorded audio.
          - sample_rate: The number of samples of audio carried per second (in Hz).
          - chunk_size: The number of frames per buffer.

          Returns:
          None
          """
          # Initialize PyAudio
          p = pyaudio.PyAudio()

          # Open a stream
          stream = p.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=sample_rate,
                          input=True,
                          frames_per_buffer=chunk_size)

          print("Recording...")

          frames = []
          while True:
              try:
                  data = stream.read(chunk_size)
                  frames.append(data)

                  # Check for silence to stop recording
                  if max(data) < 50:  # Adjust the threshold as needed
                      break

              except KeyboardInterrupt:
                  break

          print("Finished recording.")

          # Stop and close the stream
          stream.stop_stream()
          stream.close()
          p.terminate()

          # Save the recorded audio to a WAV file
          wf = wave.open(filename, 'wb')
          wf.setnchannels(1)
          wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
          wf.setframerate(sample_rate)
          wf.writeframes(b''.join(frames))
          wf.close()

      def listen_for_keyword(keyword="hello", timeout=5):
          recognizer = sr.Recognizer()

          with sr.Microphone() as source:
              print(f"Say '{keyword}' to start recording.")

              try:
                  # Set a timeout for listening after the keyword
                  audio = recognizer.listen(source, timeout=timeout)

                  # Recognize the keyword
                  spoken_text = recognizer.recognize_google(audio).lower()
                  print(f"Recognized: {spoken_text}")

                  if keyword in spoken_text:
                      print(f"Keyword '{keyword}' detected. Recording...")
                      return True

              except sr.UnknownValueError:
                  print("No voice found.")
              except sr.RequestError as e:
                  print(f"Error with the speech recognition service; {e}")

          return False

      if __name__ == "__main__":
          output_filename = "recorded_audio.wav"

          # Wait for the keyword before starting recording
          if listen_for_keyword():
              # Record audio until a period of silence is detected
              record_audio(output_filename)




              

      from openai import OpenAI
      client = OpenAI()

      audio_file = open("recorded_audio.wav", "rb")
      transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file, 
        response_format="text"
      )
      print(transcript)





      #USER PROMPT
      prompt = transcript

      #MEMORIES HOUSE
      user_conversation.append(dict(role="user", content=prompt))



      #THOUGHTS HOUSE
      response = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages= user_conversation
      )
      response_message = response.choices[0].message.content
      user_conversation.append(dict(role="assistant", content=response_message))

      print(response_message)








      #TEXT TO SPEECH CORNER
      response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=response_message,
      )

      response.stream_to_file("output.mp3")


      import pygame

      # Initialize Pygame
      pygame.init()

      # Path to the MP3 file
      mp3_file_path = "output.mp3"

      # Create a Pygame mixer
      pygame.mixer.init()

      # Load the MP3 file
      sound = pygame.mixer.Sound(mp3_file_path)

      # Play the sound
      sound.play()

      # Wait for the sound to finish playing
      pygame.time.wait(int(sound.get_length() * 1000))  # Convert seconds to milliseconds
