import io
import math
from typing import Union, BinaryIO, Tuple, List, Optional
import numpy as np
import scipy.signal
import soundfile as sf
import librosa

from vocalis.models import (
    AnalysisResponse,
    SpeechCharacteristics,
    PauseSegment,
    TimelineData,
)
from vocalis.classifier import classify_speech_style


def butter_bandpass_filter(
    data: np.ndarray, lowcut: float, highcut: float, fs: int, order: int = 4
) -> np.ndarray:
    """Apply a Butterworth bandpass filter to isolate vocal formant frequencies."""
    nyq = 0.5 * fs
    low = max(0.01, lowcut / nyq)
    high = min(0.99, highcut / nyq)
    b, a = scipy.signal.butter(order, [low, high], btype="band")
    return scipy.signal.filtfilt(b, a, data)


def butter_lowpass_filter(
    data: np.ndarray, cutoff: float, fs: int, order: int = 3
) -> np.ndarray:
    """Lowpass filter for smoothing the acoustic energy envelope."""
    nyq = 0.5 * fs
    normal_cutoff = min(0.99, cutoff / nyq)
    b, a = scipy.signal.butter(order, normal_cutoff, btype="low", analog=False)
    return scipy.signal.filtfilt(b, a, data)


class AudioAnalyzer:
    def __init__(self, target_sr: int = 16000):
        self.target_sr = target_sr
        self.hop_length = int(target_sr * 0.010)  # 10ms hop = 160 samples
        self.frame_length = 512  # 32ms frame = 512 samples (power of 2, optimal for FFT & YIN)

    def load_audio(self, audio_source: Union[str, BinaryIO, bytes]) -> Tuple[np.ndarray, float]:
        """Load audio file or byte buffer into 1D mono float32 at target sampling rate."""
        if isinstance(audio_source, bytes):
            audio_source = io.BytesIO(audio_source)

        # librosa handles resample and mono conversion cleanly
        y, sr = librosa.load(audio_source, sr=self.target_sr, mono=True)
        
        # Avoid silence or degenerate empty audio
        if len(y) == 0:
            raise ValueError("Audio file contains no audio samples.")
        
        # Normalize audio peak
        max_val = np.max(np.abs(y))
        if max_val > 0:
            y = y / max_val
            
        duration = float(len(y) / self.target_sr)
        return y.astype(np.float32), duration

    def detect_pauses_and_speech(
        self, y: np.ndarray, duration: float
    ) -> Tuple[List[PauseSegment], float, float, np.ndarray, np.ndarray]:
        """
        Segment audio into speech and pauses using adaptive bimodal energy envelopes.
        Pauses are defined as silence/breath intervals >= 200ms.
        """
        # Frame-level RMS energy
        rms = librosa.feature.rms(
            y=y, frame_length=self.frame_length, hop_length=self.hop_length
        )[0]
        
        # Convert RMS to dB relative to peak
        eps = 1e-6
        db = 20 * np.log10(np.maximum(rms, eps))
        max_db = np.max(db)
        rel_db = db - max_db
        
        frame_times = librosa.frames_to_time(
            np.arange(len(rel_db)), sr=self.target_sr, hop_length=self.hop_length
        )

        # Robust adaptive thresholding:
        # Measures ambient noise floor (p15) vs speech peak (p90)
        p15 = float(np.percentile(rel_db, 15))
        p90 = float(np.percentile(rel_db, 90))
        dyn_range = p90 - p15

        if dyn_range > 8.0:
            # Place threshold at 35% of the dynamic range above noise floor
            silence_thresh_db = p15 + 0.35 * dyn_range
        else:
            # Low dynamic range fallback
            silence_thresh_db = p90 - 7.0

        # Safety clamps
        silence_thresh_db = max(-45.0, min(-10.0, silence_thresh_db))
        is_silent_frame = rel_db < silence_thresh_db

        # 1. Collect initial silence segments (>= 80ms)
        raw_pauses: List[List[float]] = []
        in_silence = False
        silence_start = 0.0

        for t, silent in zip(frame_times, is_silent_frame):
            if silent and not in_silence:
                in_silence = True
                silence_start = t
            elif not silent and in_silence:
                in_silence = False
                silence_duration = t - silence_start
                if silence_duration >= 0.08:
                    raw_pauses.append([float(silence_start), float(t)])

        if in_silence:
            silence_duration = duration - silence_start
            if silence_duration >= 0.08:
                raw_pauses.append([float(silence_start), float(duration)])

        # 2. Bridge micro-gaps (e.g. breaths, lip smacks, mic clicks <= 180ms)
        bridge_max_sec = 0.18
        bridged: List[List[float]] = []
        for seg in raw_pauses:
            if not bridged:
                bridged.append(seg)
            else:
                prev = bridged[-1]
                gap = seg[0] - prev[1]
                if gap <= bridge_max_sec:
                    # Bridge together
                    prev[1] = seg[1]
                else:
                    bridged.append(seg)

        # 3. Filter by conversational pause threshold (>= 200ms)
        min_pause_sec = 0.20
        pauses: List[PauseSegment] = []
        for s, e in bridged:
            dur = e - s
            if dur >= min_pause_sec:
                pauses.append(
                    PauseSegment(
                        start=round(float(s), 3),
                        end=round(float(e), 3),
                        duration=round(float(dur), 3),
                    )
                )

        total_pause_duration = sum(p.duration for p in pauses)
        active_speech_duration = max(0.05, duration - total_pause_duration)

        return pauses, total_pause_duration, active_speech_duration, frame_times, rel_db

    def count_syllables(
        self, y: np.ndarray, pauses: List[PauseSegment]
    ) -> Tuple[int, List[float]]:
        """
        Count syllables acoustically using intensity peak detection in vowel formant bands
        (de Jong & Wempe algorithm principle).
        """
        # 1. Bandpass filter: isolate 300Hz - 3300Hz (vowel formants)
        filtered = butter_bandpass_filter(
            y, lowcut=300, highcut=3300, fs=self.target_sr, order=4
        )

        # 2. Extract smoothed intensity envelope
        rectified = np.abs(filtered)
        envelope = butter_lowpass_filter(
            rectified, cutoff=12.0, fs=self.target_sr, order=3
        )
        envelope = np.maximum(0.0, envelope)
        
        env_max = np.max(envelope)
        if env_max > 0:
            envelope = envelope / env_max

        # 3. Peak detection
        min_dist = int(0.100 * self.target_sr)  # 100ms minimum distance between syllables
        prominence = 0.04  # Sensitive to unstressed and conversational vowels
        peaks, _ = scipy.signal.find_peaks(
            envelope,
            distance=min_dist,
            prominence=prominence,
            height=0.03,
        )

        # 4. Filter peaks: discard peaks that fall within detected pause intervals
        syllable_times: List[float] = []
        for p in peaks:
            t = float(p / self.target_sr)
            in_pause = any(pause.start <= t <= pause.end for pause in pauses)
            if not in_pause:
                syllable_times.append(round(t, 3))

        total_syllables = len(syllable_times)
        return total_syllables, syllable_times

    def analyze_pitch_and_energy(
        self, y: np.ndarray, pauses: List[PauseSegment], frame_times: np.ndarray, rel_db: np.ndarray
    ) -> Tuple[float, str, float, str, List[Optional[float]]]:
        """
        Extract fundamental frequency F0 and analyze pitch variation in semitones.
        Extract energy variation in dB.
        """
        # Pitch tracking using YIN
        # Human vocal pitch range: 65 Hz to 420 Hz
        fmin = 65.0
        fmax = 420.0
        pitch_contour = librosa.yin(
            y,
            fmin=fmin,
            fmax=fmax,
            sr=self.target_sr,
            hop_length=self.hop_length,
            frame_length=self.frame_length,
        )

        # Filter pitch: zero out unvoiced frames or frames occurring in pauses
        pitch_hz_clean: List[Optional[float]] = []
        voiced_pitches: List[float] = []
        speech_dbs: List[float] = []

        for t, f0, db_val in zip(frame_times, pitch_contour, rel_db):
            # Is frame in a pause?
            in_pause = any(pause.start <= t <= pause.end for pause in pauses)
            
            # Voicing criteria: valid f0 and energy not in deep silence
            if not in_pause and db_val > -32.0 and not np.isnan(f0) and fmin <= f0 <= fmax:
                pitch_hz_clean.append(round(float(f0), 1))
                voiced_pitches.append(float(f0))
                speech_dbs.append(float(db_val))
            else:
                pitch_hz_clean.append(None)

        # 1. Pitch variation calculation (Semitones standard deviation)
        if len(voiced_pitches) >= 5:
            median_f0 = float(np.median(voiced_pitches))
            # Convert to semitones relative to median: 12 * log2(f0 / median)
            semitones = [12.0 * math.log2(f / median_f0) for f in voiced_pitches if f > 0]
            pitch_std_semitones = float(np.std(semitones))
            
            if pitch_std_semitones < 2.0:
                pitch_label = "Low"
            elif pitch_std_semitones <= 3.8:
                pitch_label = "Moderate"
            else:
                pitch_label = "High"
        else:
            pitch_std_semitones = 0.0
            pitch_label = "Low"

        # 2. Energy variation calculation (dB standard deviation across speech)
        if len(speech_dbs) >= 5:
            energy_std_db = float(np.std(speech_dbs))
            if energy_std_db < 3.2:
                energy_label = "Low"
            elif energy_std_db <= 6.0:
                energy_label = "Moderate"
            else:
                energy_label = "High"
        else:
            energy_std_db = 0.0
            energy_label = "Low"

        return (
            round(pitch_std_semitones, 2),
            pitch_label,
            round(energy_std_db, 1),
            energy_label,
            pitch_hz_clean,
        )

    def analyze(self, audio_source: Union[str, BinaryIO, bytes]) -> AnalysisResponse:
        """Execute full acoustic analysis pipeline."""
        y, duration = self.load_audio(audio_source)

        # Pauses & voice activity
        raw_pauses, _, _, frame_times, rel_db = (
            self.detect_pauses_and_speech(y, duration)
        )

        # Syllables & rates
        total_syllables, syllable_times = self.count_syllables(y, raw_pauses)
        
        # Determine true Speech Span (excluding lead-in and trailing recording silence):
        if len(syllable_times) > 0:
            speech_onset = max(0.0, syllable_times[0] - 0.20)
            speech_offset = min(duration, syllable_times[-1] + 0.20)
            speech_span = max(0.2, speech_offset - speech_onset)
        else:
            speech_onset = 0.0
            speech_offset = duration
            speech_span = max(0.2, duration)

        # Filter internal pauses: strictly within [speech_onset, speech_offset]
        internal_pauses: List[PauseSegment] = []
        for p in raw_pauses:
            p_start = max(speech_onset, p.start)
            p_end = min(speech_offset, p.end)
            if p_end - p_start >= 0.20:
                internal_pauses.append(
                    PauseSegment(
                        start=round(float(p_start), 3),
                        end=round(float(p_end), 3),
                        duration=round(float(p_end - p_start), 3),
                    )
                )

        total_pause_dur = sum(p.duration for p in internal_pauses)
        active_speech_dur = max(0.1, speech_span - total_pause_dur)

        # Accurate speaking rate during active delivery & articulation rate during phonation
        speaking_rate = round(total_syllables / max(0.1, speech_span), 1)
        articulation_rate = round(total_syllables / max(0.1, active_speech_dur), 1)

        # Pause statistics strictly within speech span
        pause_ratio = round((total_pause_dur / max(0.1, speech_span)) * 100.0, 1)
        avg_pause_ms = (
            round((total_pause_dur / len(internal_pauses)) * 1000.0, 1)
            if internal_pauses
            else 0.0
        )
        pause_frequency = (
            round(len(internal_pauses) / (speech_span / 60.0), 1)
            if speech_span > 0
            else 0.0
        )
        speech_to_silence = (
            round(active_speech_dur / max(0.01, total_pause_dur), 1)
            if total_pause_dur > 0
            else round(active_speech_dur * 10.0, 1)
        )

        # Pitch & Energy (computed over active speech frames)
        (
            pitch_std_semi,
            pitch_label,
            energy_std_db,
            energy_label,
            pitch_hz_clean,
        ) = self.analyze_pitch_and_energy(y, internal_pauses, frame_times, rel_db)

        # Style classification
        style_title, style_desc = classify_speech_style(
            speaking_rate=speaking_rate,
            articulation_rate=articulation_rate,
            pause_ratio=pause_ratio,
            pitch_var_label=pitch_label,
            energy_var_label=energy_label,
        )

        # Format exact plain-text card
        formatted_card = (
            "Speech Characteristics\n"
            "────────────────────────\n"
            f"Speaking rate:       {speaking_rate:.1f} syllables/sec\n"
            f"Pause ratio:         {int(round(pause_ratio))}%\n"
            f"Avg pause:           {int(round(avg_pause_ms))} ms\n"
            f"Pitch variation:     {pitch_label}\n"
            f"Energy variation:    {energy_label}\n\n"
            "Style:\n"
            f"{style_title}"
        )

        # Downsample timeline data for clean Web UI visualization
        downsample_factor = max(1, len(frame_times) // 300)
        ds_times = [round(float(t), 3) for t in frame_times[::downsample_factor]]
        ds_energy = [round(float(db), 1) for db in rel_db[::downsample_factor]]
        ds_pitch = pitch_hz_clean[::downsample_factor]

        # Waveform downsampling (min/max or rms)
        wave_step = max(1, len(y) // 300)
        ds_wave = [round(float(v), 3) for v in y[::wave_step]]

        timeline = TimelineData(
            time_points=ds_times,
            waveform=ds_wave,
            energy_db=ds_energy,
            pitch_hz=ds_pitch,
            syllable_times=syllable_times,
            pauses=internal_pauses,
        )

        characteristics = SpeechCharacteristics(
            speaking_rate=speaking_rate,
            articulation_rate=articulation_rate,
            pause_ratio=pause_ratio,
            avg_pause_ms=avg_pause_ms,
            pause_frequency=pause_frequency,
            speech_to_silence_ratio=speech_to_silence,
            pitch_variation_label=pitch_label,
            pitch_variation_semitones=pitch_std_semi,
            energy_variation_label=energy_label,
            energy_variation_db=energy_std_db,
            style=style_title,
            style_description=style_desc,
        )

        return AnalysisResponse(
            duration_seconds=round(duration, 2),
            total_syllables=total_syllables,
            characteristics=characteristics,
            timeline=timeline,
            formatted_card=formatted_card,
        )
