"""Блок 1 — расшифровка ролика 18 через OpenAI Whisper API (пословные тайминги).

Результат: videos/18/whisper_raw.json (сырой ответ API). Уточнение границ — snap1.py.
"""
import os, subprocess, json

BUILD = os.path.dirname(os.path.abspath(__file__))
VID = f"{BUILD}/../videos/18"
AUD = f"{VID}/audio16k.mp3"


def key():
    for line in open(f"{BUILD}/.env", encoding="utf-8"):
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("нет OPENAI_API_KEY в build/.env")


def main():
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"{VID}/source_raw.mp4",
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k", AUD], check=True)
    subprocess.run(["curl", "-s", "https://api.openai.com/v1/audio/transcriptions",
                    "-H", f"Authorization: Bearer {key()}", "-F", f"file=@{AUD}",
                    "-F", "model=whisper-1", "-F", "language=ru", "-F", "response_format=verbose_json",
                    "-F", "timestamp_granularities[]=word", "-F", "timestamp_granularities[]=segment",
                    "-o", f"{VID}/whisper_raw.json"], check=True)
    d = json.load(open(f"{VID}/whisper_raw.json", encoding="utf-8"))
    print(len(d["words"]), "слов")
    # §1: сверка текста вторым распознаванием (whisper-1 ошибается: «откройте срать» вместо «тетрадь», ролик 8)
    subprocess.run(["curl", "-s", "https://api.openai.com/v1/audio/transcriptions",
                    "-H", f"Authorization: Bearer {key()}", "-F", f"file=@{AUD}",
                    "-F", "model=gpt-4o-transcribe", "-F", "language=ru", "-F", "response_format=json",
                    "-o", f"{VID}/gpt4o_text.json"], check=True)
    print("gpt-4o:", json.load(open(f"{VID}/gpt4o_text.json", encoding="utf-8")).get("text", "")[:2000])


if __name__ == "__main__":
    main()
