# Vocalis 🎙️

An interactive acoustic speech delivery and vocal dynamics analyzer. Vocalis evaluates spoken recordings by measuring speaking rate against active articulation, silence gaps, pitch contours, and volume shifts — providing speakers with objective, data-backed feedback to eliminate monotone delivery, fix rushed pacing, and master rhetorical pauses.

---

## ⚡ Output Overview

```
Speech Characteristics
────────────────────────
Speaking rate:       4.1 syllables/sec
Pause ratio:         18%
Avg pause:           420 ms
Pitch variation:     Moderate
Energy variation:    High

Style:
Fast / expressive speech
```

---

## 🔬 How the Metrics Are Measured (Pure Acoustic DSP)

Vocalis relies on **deterministic digital signal processing (DSP)** and acoustic linguistics without requiring heavy speech-to-text models or cloud APIs:

1. **Speaking Rate & Articulation Rate (syllables/sec):**
   - Implements the **de Jong & Wempe vowel nuclei detection algorithm**.
   - Filters speech to the human vowel formant range (300 Hz – 3300 Hz) and tracks energy peaks coinciding with voiced phonation.
   - *Speaking rate* = syllables / total recording time.
   - *Articulation rate* = syllables / active phonated time (pauses removed).
2. **Pause Architecture & Silence Gaps:**
   - Detects contiguous silent intervals $\ge 250\text{ ms}$ (the linguistic boundary distinguishing pauses from stop consonants).
   - Reports **Pause Ratio (%)**, **Average Pause Duration (ms)**, **Pause Frequency (pauses/min)**, and **Speech-to-Silence Ratio**.
3. **Pitch Variation ($F_0$ Tracking):**
   - Tracks fundamental frequency contours using YIN/pYIN autocorrelation.
   - Computes standard deviation in semitones relative to median pitch:
     - `< 2.0 semitones` $\to$ **Low (Monotone)**
     - `2.0 – 3.8 semitones` $\to$ **Moderate**
     - `> 3.8 semitones` $\to$ **High (Expressive)**
4. **Energy / Loudness Dynamics:**
   - Evaluates RMS dynamic range and standard deviation across voiced frames to identify flat volume vs. punchy vocal projection.
5. **Style Classification:**
   - Synthesizes pace, dynamics, and pause metrics into intuitive archetypes (e.g., *Fast / expressive speech*, *Deliberate / authoritative*, *Steady / flat delivery*).

---

## 🚀 Quick Start

### 1. Launch the Web UI on Localhost

```bash
./run.sh
# OR manually:
.venv/bin/python main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

- **Record Speech:** Use your live microphone with a real-time waveform visualizer (records uncompressed 16-bit PCM WAV directly in browser).
- **Upload File:** Drag and drop any `.wav`, `.mp3`, `.m4a`, `.ogg`, or `.flac` audio file.
- **Try Demo Audio:** Instant one-click test with pre-synthesized acoustic speech.
- **Acoustic Timeline:** View interactive waveforms, highlighted pause segments, syllable markers, and pitch ($F_0$) overlays.

---

### 2. Run via CLI

Analyze any audio recording from your terminal:

```bash
# Standard scorecard
.venv/bin/python cli.py sample_test.wav

# Extended analytics
.venv/bin/python cli.py sample_test.wav --details

# JSON format
.venv/bin/python cli.py sample_test.wav --json
```

