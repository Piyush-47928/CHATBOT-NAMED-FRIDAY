# 🤖 Friday A.I – Voice Assistant in Python
![Python](https://img.shields.io/badge/Language-Python-yellow)
![Status](https://img.shields.io/badge/Status-Active-success)


Friday A.I is a Python-based voice assistant that can listen to your voice commands, respond using speech, open websites, tell the current time, perform Google searches, and even capture photos using your webcam.

This project is ideal for beginners in Python, AI, and voice-based applications, especially students working on mini-projects or learning automation.

---

## ✨**Features**

- 🎤 Voice input using microphone  
- 🔊 Text-to-speech response (Windows SAPI)
- 🌐 Open websites via voice commands
- 🔍 Search queries using voice
- ⏰ Tell current system time
- 📷 Capture photos using webcam
- 🧠 Simple command-processing logic

---

## 🛠️ **Technologies & Libraries Used**
  
- Python 3
- win32com.client – Text-to-Speech (Windows only)
- speech_recognition – Speech to text
- pygame & pygame.camera – Webcam access
- webbrowser – Open websites
- datetime – Time handling
- os – System commands

---

## 📁 **Project Structure**

```bash
CHATBOT-NAMED-FRIDAY/
│
├── WITHOUT_API
├── OPEN_API_KEY
└── README.md          # Project documentation

```

---

## ⚙️**Installation & Setup**
### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Piyush-47928/CHATBOT-NAMED-FRIDAY
cd CHATBOT-NAMED-FRIDAY
```

### 2️⃣ Install Required Libraries
```bash
pip install pywin32 SpeechRecognition pygame pyaudio
```


## ⚠️Note:
> This project works only on Windows because it uses SAPI.SpVoice.
> Make sure your microphone and webcam are working properly.
> For pyaudio, you may need a precompiled wheel on Windows.


##  👨‍💻 Author
PIYUSH SHARMA | PYTHON DEVELOPER | B.TECH
