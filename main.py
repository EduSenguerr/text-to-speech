import pyttsx3


def text_to_speech(text: str) -> None:
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def main():
    user_text = input("Enter the text you want to convert to speech: ")
    text_to_speech(user_text)


if __name__ == "__main__":
    main()
