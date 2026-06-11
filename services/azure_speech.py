import azure.cognitiveservices.speech as speechsdk

from core.config import settings


def get_speech_config():
    return speechsdk.SpeechConfig(
        subscription=settings.AZURE_SPEECH_KEY, region=settings.AZURE_SPEECH_REGION
    )


async def assess_pronunciation(audio_file_path: str, reference_text: str):
    pass
