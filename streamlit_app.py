import base64
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from vocalis.analyzer import AudioAnalyzer

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Vocalis - Speech Delivery & Dynamics Analyzer",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Global Chrome Removal & Seamless Dark Container Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Hide all Streamlit native navigation and chrome */
        #MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Full viewport reset for seamless custom UI embedding */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main, .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100vw !important;
            width: 100% !important;
            background-color: #0a0d14 !important;
            overflow-x: hidden !important;
        }

        /* Component iframe styling */
        iframe[data-testid="stCustomComponentV1"], iframe {
            border: none !important;
            width: 100% !important;
            min-height: 100vh !important;
            display: block !important;
            background-color: #0a0d14 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Component Setup & Acoustic Engine Initialization
# -----------------------------------------------------------------------------
frontend_dir = Path(__file__).parent / "frontend"
vocalis_component = components.declare_component("vocalis_ui", path=str(frontend_dir))

if "analyzer" not in st.session_state:
    st.session_state["analyzer"] = AudioAnalyzer()

if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None

if "audio_b64" not in st.session_state:
    st.session_state["audio_b64"] = None

if "error" not in st.session_state:
    st.session_state["error"] = None

if "processed_req_id" not in st.session_state:
    st.session_state["processed_req_id"] = None

# Render the custom UI component
client_data = vocalis_component(
    result=st.session_state["analysis_result"],
    audio_b64=st.session_state["audio_b64"],
    error=st.session_state["error"],
    key="vocalis_app_instance",
)

# -----------------------------------------------------------------------------
# Handle Interactive Actions from Custom Component
# -----------------------------------------------------------------------------
if client_data and isinstance(client_data, dict):
    req_id = client_data.get("req_id")
    if req_id and req_id != st.session_state["processed_req_id"]:
        st.session_state["processed_req_id"] = req_id
        action = client_data.get("action")

        try:
            if action == "analyze":
                audio_b64 = client_data.get("audio_b64")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    result = st.session_state["analyzer"].analyze(audio_bytes)
                    st.session_state["analysis_result"] = result.model_dump()
                    st.session_state["audio_b64"] = audio_b64
                    st.session_state["error"] = None
                    st.rerun()

            elif action == "sample":
                sample_file = Path(__file__).parent / "sample_test.wav"
                with open(sample_file, "rb") as f:
                    audio_bytes = f.read()
                result = st.session_state["analyzer"].analyze(audio_bytes)
                st.session_state["analysis_result"] = result.model_dump()
                st.session_state["audio_b64"] = base64.b64encode(audio_bytes).decode("ascii")
                st.session_state["error"] = None
                st.rerun()

        except Exception as e:
            st.session_state["error"] = str(e)
            st.rerun()
