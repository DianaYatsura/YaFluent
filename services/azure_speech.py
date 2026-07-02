import json

import azure.cognitiveservices.speech as speechsdk

from core.config import settings


class AzurePronunciationService:
    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY, region=settings.AZURE_SPEECH_REGION
        )

    def assess_pronunciation(self, audio_path: str, reference_text: str):
        audio_config = speechsdk.AudioConfig(filename=audio_path)

        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )

        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config,
            language="en-US",
        )
        pronunciation_config.apply_to(recognizer)

        result = recognizer.recognize_once()

        pronunciation_result_json = result.properties.get(
            speechsdk.PropertyId.SpeechServiceResponse_JsonResult
        )
        return json.loads(pronunciation_result_json)


azure_service = AzurePronunciationService()
