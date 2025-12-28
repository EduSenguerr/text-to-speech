import pyttsx3 

engine = pyttsx3.init()

text = "Hi, this is my first text to speech project on python"

engine.say(text)
engine.runAndWait()
