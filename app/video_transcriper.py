from dataclasses import dataclass
from youtube_transcript_api import YouTubeTranscriptApi

@dataclass
class VideoTranscript:
    
    logger:any

    def __post_init__(self):
        self.logger.info(f"Video Transcipt post_init")
        self.ytt_api = YouTubeTranscriptApi()


    def transcript(self, video_id: str, language: str):
        transcript = self.ytt_api.fetch(str(video_id), languages=[language])
        all_texts = []

        for snippet in transcript:
            all_texts.append(snippet.text)

        full_text = " ".join(all_texts)

        return full_text







