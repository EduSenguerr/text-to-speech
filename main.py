import pyttsx3


def text_to_speech(text: str, filename: str | None = None) -> None:
    engine = pyttsx3.init()

    if filename:
        engine.save_to_file(text, filename)
    else:
        engine.say(text)

    engine.runAndWait()


def main():
    user_text = input("Enter the text you want to convert to speech: ")
    save_audio = input("Do you want to save the audio? (y/n): ").lower()

    if save_audio == "y":
        filename = "output.mp3"
        text_to_speech(user_text, filename)
        print(f"Audio saved as {filename}")
    else:
        text_to_speech(user_text)


if __name__ == "__main__":
    main()
