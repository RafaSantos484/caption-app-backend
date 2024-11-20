import shutil
from dotenv import load_dotenv
from typing import Optional
from fastapi import FastAPI, File, Form, HTTPException
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import uvicorn
# import whisper
from openai import OpenAI

from .utils import generate_random_id, remove_if_exists

load_dotenv()

client = OpenAI()
app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://caption-app-frontend.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# model = whisper.load_model("small")
# model = whisper.load_model("medium")


@app.get("/")
def hello_world():
    return {"ok": True, "message": "Hello World!"}


def apply_caption(video: VideoFileClip, segments: list, id: str):
    clips = [video]
    for segment in segments:
        start, end, text = segment['start'], segment['end'], segment['text']

        if not text:
            print("Skipping empty transcription")
            continue
        if "amara.org" in text.lower():
            print("Skipping transcription with amara.org")
            continue

        subtitle = TextClip(
            text,
            color='white',
            bg_color='black',
            size=(video.w, video.h*0.15),
            method="caption",
        ).set_position(('center', 'bottom')).set_start(start).set_duration(end - start)

        clips.append(subtitle)

    video_with_subtitles = CompositeVideoClip(clips)
    output_filename = f"{id}_with_subtitles.mp4"
    video_with_subtitles.write_videofile(
        output_filename, codec="libx264", logger=None)
    return output_filename


@app.post("/")
def apply_caption_to_video(request_video: UploadFile = File(...), language: Optional[str] = Form(None)):
    id = generate_random_id()
    video_format = request_video.filename.split(".")[-1]
    video_filename = f"{id}.{video_format}"
    try:
        with open(video_filename, "wb") as buffer:
            shutil.copyfileobj(request_video.file, buffer)
    except Exception as e:
        print(e)
        remove_if_exists(video_filename)
        raise HTTPException(
            status_code=500, detail="Falha ao tentar salvar arquivo de vídeo")

    audio_filename = f"{id}.mp3"
    try:
        video = VideoFileClip(video_filename)
        video.audio.write_audiofile(audio_filename, logger=None)
        audiofile = open(audio_filename, "rb")
    except Exception as e:
        print(e)
        remove_if_exists(video_filename)
        remove_if_exists(audio_filename)
        raise HTTPException(
            status_code=500, detail="Falha ao tentar extrair áudio do vídeo")

    try:
        '''
        result = model.transcribe(audio_filename,
                                  language=language,
                                  best_of=5,
                                  beam_size=5,
                                  patience=2,
                                  condition_on_previous_text=False,
                                  verbose=False)
        '''

        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audiofile,
            language=language,
            timestamp_granularities=["segment"],
            response_format="verbose_json"
        )
        result = transcription.model_dump()
        return result
    except Exception as e:
        print(e)
        # remove_if_exists(video_filename)
        raise HTTPException(
            status_code=500, detail="Falha ao tentar transcrever áudio")
    finally:
        video.close()
        audiofile.close()
        remove_if_exists(audio_filename)
        remove_if_exists(video_filename)

    '''
    try:
        output_filename = apply_caption(video, result["segments"], id)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500, detail="Falha ao tentar aplicar legendas")
    finally:
        video.close()
        remove_if_exists(video_filename)

    request_video_filename = request_video.filename.split(".")[0]

    def delete_output_file():
        remove_if_exists(output_filename)
    return FileResponse(output_filename,
                        media_type="video/mp4",
                        filename=f"{request_video_filename}_with_subtitles.mp4",
                        background=BackgroundTask(delete_output_file))
    '''


def run():
    uvicorn.run(app="caption_generator_backend.index:app",
                host="0.0.0.0", port=8000, workers=1)
