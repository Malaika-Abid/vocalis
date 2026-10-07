import numpy as np
import soundfile as sf
from vocalis.analyzer import AudioAnalyzer

def generate_sample_speech_audio(filepath: str, duration: float = 6.0, sr: int = 16000):
    """
    Synthesize a clean speech-like audio sample with vowel syllables and intentional pauses.
    """
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = np.zeros_like(t)

    # Simulate speaking with pauses:
    # Segment 1: 0.0 - 2.2s (speaking)
    # Pause 1:   2.2 - 2.8s (600ms pause)
    # Segment 2: 2.8 - 4.5s (speaking)
    # Pause 2:   4.5 - 5.0s (500ms pause)
    # Segment 3: 5.0 - 5.8s (speaking)
    # End pause: 5.8 - 6.0s
    speech_intervals = [(0.2, 2.2), (2.8, 4.5), (5.0, 5.8)]

    # In speech intervals, generate syllable pulses (~4 syllables per second)
    syllable_rate = 4.0
    for start, end in speech_intervals:
        dur = end - start
        num_syls = int(dur * syllable_rate)
        syl_spacing = dur / num_syls
        for i in range(num_syls):
            syl_start = start + i * syl_spacing
            syl_center = syl_start + 0.10
            # Vowel Gaussian envelope
            env = np.exp(-0.5 * ((t - syl_center) / 0.04) ** 2)
            # Modulate with pitch (e.g. 150 Hz to 180 Hz)
            f0 = 160 + 25 * np.sin(2 * np.pi * 1.5 * t)
            carrier = np.sin(2 * np.pi * f0 * t) + 0.4 * np.sin(2 * np.pi * 2 * f0 * t)
            # Add vowel resonance formant
            formant = np.sin(2 * np.pi * 800 * t) * 0.3
            audio += env * (carrier + formant)

    # Normalize
    audio = audio / (np.max(np.abs(audio)) + 1e-6)
    sf.write(filepath, audio, sr)
    print(f"Generated sample audio: {filepath}")

if __name__ == "__main__":
    test_wav = "sample_test.wav"
    generate_sample_speech_audio(test_wav)

    analyzer = AudioAnalyzer()
    res = analyzer.analyze(test_wav)
    print("\n--- OUTPUT CARD ---")
    print(res.formatted_card)
    print("\n--- DETAILED METRICS ---")
    print(f"Total Syllables: {res.total_syllables}")
    print(f"Duration: {res.duration_seconds}s")
    print(f"Articulation Rate: {res.characteristics.articulation_rate} syl/s")
    print(f"Speech-to-silence: {res.characteristics.speech_to_silence_ratio}")
    print(f"Pitch Semitones SD: {res.characteristics.pitch_variation_semitones}")
    print(f"Energy dB SD: {res.characteristics.energy_variation_db}")
    print(f"Style Description: {res.characteristics.style_description}")

