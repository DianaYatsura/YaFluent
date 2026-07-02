from pydub import AudioSegment


def convert_ogg_to_wav(input_path: str, output_path: str):
    audio = AudioSegment.from_ogg(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_path, format="wav")
