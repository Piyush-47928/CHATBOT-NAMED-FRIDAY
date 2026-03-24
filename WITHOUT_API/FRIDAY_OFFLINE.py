import win32com.client
import speech_recognition as sr
import webbrowser
import os
import openai
import datetime
import pygame
import pygame.camera


speaker = win32com.client.Dispatch("SAPI.spVoice")


# sr.Recognizer()
def cmr(imnme):
    pygame.camera.init()
    caml = pygame.camera.list_cameras()
    if caml:
        cam = pygame.camera.Camera(caml[0],(640,480))
        cam.start()
        image = cam.get_image()
        pygame.image.save(image, f"{inme.jpg}")
    else:
        print(f"sorry I am not able to take your photo.., From - Friday")

def say(a):
    speaker.speak(a)
    print(a)

def takecommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 0.6
        audio = r.listen(source)  # Add timeout and phrase_time_limit parameters

    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"You said: {query}")
    except Exception as e:
        print(e)
        print("Sorry, I didn't get that. Can you please repeat?")
        return "None"
    
    return query



def greeting(gr, nme):
    if "Goodbye" in gr:
        print(f"Goodbye, {nme}")
    elif "":
        print()

def dt():
    a = datetime.datetime.now().strftime("%H:%M:%S")
    return a

say("Hello I am Friday A.I")
cmd_lett = []
say("What is your name?")
nme = takecommand()
say = (f"Hello! {nme}, how may I help you ?")

while True:
    print("Line67...")
    task = takecommand()

    if f"Open the site" in task.lower():
        spt_web = task.split(" ")
        for i in spt_web:
            if i == "site":
                sch = i + 1
            break
        webbrowser.open(f"https://www.{sch}.com")
    elif f"Please search " in task.lower():
        spt_sch = task.split()
        lsch = len(spt_sch)
        for i in range(lsch):
            if spt_sch[i] == "search":
                for j in range(i + 1, lsch):
                    cmd_lett.append(spt_sch[j])
                    cmd_lett.append()
    elif f"What's the time".lower() in task.lower():
        ti = dt()
        say(ti)
    elif f"Take a photo".lower() in task.lower():
        say("What you will name your photo?")
        inme = takecommand()
        cmr(inme)
        os.system("")
    else:
        pass











