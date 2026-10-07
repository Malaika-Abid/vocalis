from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class PauseSegment(BaseModel):
    start: float
    end: float
    duration: float

class SpeechCharacteristics(BaseModel):
    speaking_rate: float            # syllables / total sec
    articulation_rate: float        # syllables / speech sec
    pause_ratio: float              # percentage (e.g. 18.0)
    avg_pause_ms: float             # average pause in ms (e.g. 420.0)
    pause_frequency: float          # pauses per minute
    speech_to_silence_ratio: float  # active speech / total pause time
    pitch_variation_label: str      # Low / Moderate / High
    pitch_variation_semitones: float # standard deviation in semitones
    energy_variation_label: str     # Low / Moderate / High
    energy_variation_db: float      # standard deviation in dB
    style: str                      # e.g. "Fast / expressive speech"
    style_description: str          # friendly coaching explanation

class TimelineData(BaseModel):
    time_points: List[float]
    waveform: List[float]
    energy_db: List[float]
    pitch_hz: List[Optional[float]]
    syllable_times: List[float]
    pauses: List[PauseSegment]

class AnalysisResponse(BaseModel):
    duration_seconds: float
    total_syllables: int
    characteristics: SpeechCharacteristics
    timeline: Optional[TimelineData] = None
    formatted_card: str

