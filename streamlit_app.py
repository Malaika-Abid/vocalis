import io
from pathlib import Path
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from vocalis.analyzer import AudioAnalyzer

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Vocalis • Acoustic Speech Dynamics Analyzer",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Styling (Dark aesthetic matching Vocalis design)
st.markdown(
    """
    <style>
    .main {
        background-color: #0a0d14;
    }
    .stApp {
        background-color: #0a0d14;
        color: #f3f4f6;
    }
    .title-container {
        text-align: center;
        padding: 1.5rem 0 2rem 0;
    }
    .title-heading {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 30%, #93c5fd 80%, #c4b5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #9ca3af;
        font-size: 1.1rem;
        max-width: 680px;
        margin: 0 auto;
    }
    .metric-card {
        background: #111622;
        border: 1px solid #1e2638;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .coach-box {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.4), rgba(15, 23, 42, 0.4));
        border: 1px solid rgba(139, 92, 246, 0.35);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 1.5rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="title-container">
        <h1 class="title-heading">🎙️ Vocalis</h1>
        <p class="subtitle">Objective speech delivery & vocal presence analyzer. Evaluate pace, articulation speed, pause architecture, pitch range, and volume shifts.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize Analyzer
@st.cache_resource
def get_analyzer():
    return AudioAnalyzer()

analyzer = get_analyzer()

# -----------------------------------------------------------------------------
# Input Selection: File Upload / Mic / Demo
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("1. Provide Spoken Audio")
    
    tab_mic, tab_upload, tab_demo = st.tabs(["🎤 Record Microphone", "📁 Upload Audio File", "⚡ Try Demo Audio"])
    
    audio_source = None
    audio_bytes = None
    source_label = ""

    # Tab 1: Microphone (Native in Streamlit)
    with tab_mic:
        st.write("Click below to record your voice:")
        mic_audio = st.audio_input("Record speech")
        if mic_audio is not None:
            audio_bytes = mic_audio.read()
            source_label = "Microphone Recording"

    # Tab 2: Upload File
    with tab_upload:
        uploaded_file = st.file_uploader(
            "Choose a speech recording",
            type=["wav", "mp3", "m4a", "ogg", "flac"],
            help="Supports standard audio formats",
        )
        if uploaded_file is not None:
            audio_bytes = uploaded_file.read()
            source_label = f"Uploaded: {uploaded_file.name}"

    # Tab 3: Demo Sample
    with tab_demo:
        st.write("Test Vocalis with our pre-calibrated sample audio:")
        if st.button("Load Demo Sample"):
            sample_path = Path("sample_test.wav")
            if sample_path.exists():
                audio_bytes = sample_path.read_bytes()
                source_label = "Demo Audio Sample (sample_test.wav)"
            else:
                st.error("Demo file sample_test.wav not found.")

with col2:
    st.subheader("About Vocalis Metrics")
    st.markdown(
        """
        - **Speaking Rate:** Syllables spoken per total speech second.
        - **Articulation Rate:** Syllables per second strictly during phonated speech (excluding pauses).
        - **Pause Architecture:** Duration, frequency, and percentage of conversational silence ($\ge 200\text{ ms}$).
        - **Pitch Inflection ($F_0$):** Semitone variance diagnosing flat/monotone delivery vs. expressive range.
        - **Volume Dynamics:** Energy projection and dynamic range across sentences.
        """
    )

# -----------------------------------------------------------------------------
# Execution & Results
# -----------------------------------------------------------------------------
if audio_bytes is not None:
    st.divider()
    st.success(f"Processing: **{source_label}**")
    
    with st.spinner("Analyzing acoustic prosody, syllable nuclei, pauses, and pitch..."):
        try:
            result = analyzer.analyze(audio_bytes)
            c = result.characteristics
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # Audio Playback
    st.audio(audio_bytes)

    # 1. Plain ASCII Monospace Scorecard
    st.subheader("Speech Characteristics Scorecard")
    st.code(result.formatted_card, language="text")

    # 2. Style & Coaching Advice Callout
    st.markdown(
        f"""
        <div class="coach-box">
            <h3 style="color: #a78bfa; margin-top: 0; font-size: 1.2rem;">Style Verdict: {c.style}</h3>
            <p style="color: #e2e8f0; font-size: 1rem; margin-bottom: 0;">{c.style_description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Key Metrics Columns
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric(
            label="Speaking Rate",
            value=f"{c.speaking_rate:.1f} syl/s",
            help="Optimal keynote pace: 3.5 - 4.5 syl/s",
        )
    with m2:
        st.metric(
            label="Articulation Rate",
            value=f"{c.articulation_rate:.1f} syl/s",
            help="Rate excluding pause intervals",
        )
    with m3:
        st.metric(
            label="Pause Ratio",
            value=f"{int(round(c.pause_ratio))}%",
            help="Target for clear delivery: 15% - 25%",
        )
    with m4:
        st.metric(
            label="Avg Pause",
            value=f"{int(round(c.avg_pause_ms))} ms",
            help="Average duration of conversational pauses",
        )
    with m5:
        st.metric(
            label="Pitch Variation",
            value=c.pitch_variation_label,
            delta=f"±{c.pitch_variation_semitones} st",
            delta_color="off",
            help="Standard deviation in semitones",
        )
    with m6:
        st.metric(
            label="Energy Dynamics",
            value=c.energy_variation_label,
            delta=f"±{c.energy_variation_db} dB",
            delta_color="off",
            help="RMS dynamic projection variance",
        )

    # 4. Acoustic Timeline Chart
    if result.timeline:
        st.subheader("Acoustic Timeline Visualizer")
        tl = result.timeline
        dur = result.duration_seconds

        fig, ax = plt.subplots(figsize=(12, 3.2), facecolor="#090c14")
        ax.set_facecolor("#090c14")

        # 1. Waveform
        if tl.waveform:
            w_times = np.linspace(0, dur, len(tl.waveform))
            ax.plot(w_times, tl.waveform, color="#3b82f6", alpha=0.85, linewidth=1.2, label="Waveform")

        # 2. Highlight Pauses
        if tl.pauses:
            for p in tl.pauses:
                ax.axvspan(p.start, p.end, color="#ef4444", alpha=0.3, label="Pause (≥200ms)")

        # 3. Pitch Curve
        if tl.pitch_hz:
            p_times = tl.time_points
            valid_pitches = [p if p is not None else np.nan for p in tl.pitch_hz]
            # Normalize pitch to waveform height scale [-1, 1]
            non_nan = [p for p in valid_pitches if not np.isnan(p)]
            if non_nan:
                p_min, p_max = np.min(non_nan), np.max(non_nan)
                p_range = max(30.0, p_max - p_min)
                norm_pitch = [0.1 + 0.8 * ((p - p_min) / p_range) if not np.isnan(p) else np.nan for p in valid_pitches]
                ax.plot(p_times[:len(norm_pitch)], norm_pitch, color="#f59e0b", linewidth=1.8, label="Pitch (F0)")

        # 4. Syllable Markers
        if tl.syllable_times:
            ax.scatter(tl.syllable_times, [-0.85] * len(tl.syllable_times), color="#10b981", s=25, zorder=5, label="Syllables")

        ax.set_xlim(0, dur)
        ax.set_ylim(-1.05, 1.05)
        ax.tick_params(colors="#9ca3af", labelsize=9)
        ax.spines["bottom"].set_color("#1f2937")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#1f2937")
        ax.set_xlabel("Time (seconds)", color="#9ca3af", fontsize=10)
        ax.set_ylabel("Amplitude / Dynamics", color="#9ca3af", fontsize=10)

        # Remove duplicate labels in legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", facecolor="#111622", edgecolor="#1e2638", labelcolor="#e2e8f0", fontsize=8)

        st.pyplot(fig)
        plt.close(fig)

