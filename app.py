"""
Streamlit web interface for the AI Performance Coaching Framework.
Provides an interactive UI for analyzing frame descriptions and generating coaching recommendations.
"""

import streamlit as st
import json
import time
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from src.coaching_engine import CoachingEngine, AnalysisSession
from src.config import Config
from src.prompt_manager import PromptManager
from src.utils import safe_json_parse

# Page configuration
st.set_page_config(
    page_title="AI Performance Coach",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #1E88E5;
    text-align: center;
    margin-bottom: 2rem;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.success-message {
    background: #d4edda;
    color: #155724;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #c3e6cb;
}

.error-message {
    background: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #f5c6cb;
}

.stProgress > div > div {
    background: linear-gradient(90deg, #1E88E5, #42A5F5);
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'engine' not in st.session_state:
        st.session_state.engine = None
    if 'current_session' not in st.session_state:
        st.session_state.current_session = None
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'progress_message' not in st.session_state:
        st.session_state.progress_message = ""
    if 'progress_value' not in st.session_state:
        st.session_state.progress_value = 0.0

def check_api_key():
    """Check if API key is configured."""
    if not Config.validate_api_key():
        st.error("🔑 OpenAI API key is not configured!")
        st.info("Please set your OPENAI_API_KEY in the environment variables or .env file.")
        return False
    return True

def streamlit_progress_callback(message: str, progress: float):
    """Progress callback for Streamlit operations."""
    st.session_state.progress_message = message
    st.session_state.progress_value = progress

@st.cache_data
def get_available_templates():
    """Get available prompt templates (cached)."""
    prompt_manager = PromptManager()
    return prompt_manager.get_available_templates()

def main():
    """Main Streamlit application."""
    init_session_state()

    # Header
    st.markdown('<h1 class="main-header">🚀 AI Performance Coach</h1>', unsafe_allow_html=True)
    st.markdown("**Analyze screen recordings and get evidence-based productivity recommendations using GPT-5 with web search**")

    # Check API key
    if not check_api_key():
        return

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Settings
        st.subheader("API Settings")
        model_name = st.selectbox(
            "Model",
            options=["gpt-5", "gpt-4-turbo", "gpt-4"],
            index=0,
            help="OpenAI model to use for analysis"
        )

        reasoning_effort = st.selectbox(
            "Reasoning Effort",
            options=["minimal", "low", "medium", "high"],
            index=2,
            help="GPT-5 reasoning effort level"
        )

        # Processing Settings
        st.subheader("Processing Settings")
        interval_minutes = st.slider(
            "Chunking Interval (minutes)",
            min_value=0.5,
            max_value=10.0,
            value=2.0,
            step=0.5,
            help="Time interval for chunking frame descriptions"
        )

        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=8000,
            value=4000,
            step=100,
            help="Maximum tokens per API call"
        )

        # Note: Temperature parameter removed - not supported by GPT-5
        st.info("💡 GPT-5 uses default temperature (no customization available)")

    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "📝 Templates", "📈 Results", "🔧 System Test"])

    # Analysis Tab
    with tab1:
        st.header("Frame Description Analysis")

        # Template selection
        col1, col2 = st.columns([2, 1])

        with col1:
            template_options = ["default"] + list(get_available_templates().keys())
            selected_template = st.selectbox(
                "Coaching Focus Template",
                options=template_options,
                help="Choose a template that matches your analysis focus"
            )

            if selected_template != "default":
                template_info = get_available_templates()[selected_template]
                st.info(f"📋 **{selected_template}**: {template_info}")

        with col2:
            st.metric("Model", model_name)
            st.metric("Reasoning", reasoning_effort.title())

        # Frame data input
        st.subheader("Frame Descriptions Input")
        input_method = st.radio(
            "Input Method",
            options=["Paste JSON", "Upload File"],
            horizontal=True
        )

        frame_data = None

        if input_method == "Paste JSON":
            frame_data = st.text_area(
                "Frame Descriptions (JSON)",
                height=200,
                placeholder='{\n  "frames": [\n    {\n      "timestamp": 0.5,\n      "description": "User opening Chrome browser"\n    },\n    {\n      "timestamp": 2.1,\n      "description": "Typing in search bar"\n    }\n  ]\n}',
                help="Paste your frame description JSON here"
            )
        else:
            uploaded_file = st.file_uploader(
                "Upload Frame Description File",
                type=['json', 'txt'],
                help="Upload a JSON file containing frame descriptions"
            )

            if uploaded_file is not None:
                try:
                    if uploaded_file.type == "application/json":
                        frame_data = uploaded_file.read().decode('utf-8')
                    else:
                        frame_data = str(uploaded_file.read(), 'utf-8')
                except Exception as e:
                    st.error(f"Error reading file: {e}")

        # Validation
        if frame_data:
            with st.expander("🔍 Validate Frame Data"):
                success, parsed_data, error = safe_json_parse(frame_data)

                if success:
                    # Quick validation
                    from src.frame_processor import FrameProcessor
                    processor = FrameProcessor()
                    validation_result = processor.validate_frame_data(parsed_data)

                    if validation_result['valid']:
                        st.success("✅ Frame data is valid!")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Frames", validation_result['frame_count'])
                        with col2:
                            st.metric("Has Timestamps", "✅" if validation_result['has_timestamps'] else "❌")
                        with col3:
                            st.metric("Has Descriptions", "✅" if validation_result['has_descriptions'] else "❌")
                    else:
                        st.error("❌ Validation failed:")
                        for error_msg in validation_result['errors']:
                            st.error(f"• {error_msg}")
                else:
                    st.error(f"❌ Invalid JSON: {error}")

        # Analysis button and progress
        if st.button("🚀 Start Analysis", type="primary", disabled=not frame_data):
            if frame_data:
                try:
                    # Prepare API settings
                    api_settings = {
                        'model_name': model_name,
                        'reasoning_effort': reasoning_effort,
                        'max_tokens': max_tokens,
                        # Note: temperature removed - not supported by GPT-5
                    }

                    # Initialize engine with progress callback
                    st.session_state.engine = CoachingEngine(
                        progress_callback=streamlit_progress_callback
                    )

                    # Progress tracking
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()

                    # Run analysis
                    with st.spinner("Analyzing frame descriptions..."):
                        session = st.session_state.engine.analyze_frames(
                            frame_data=frame_data,
                            interval_minutes=interval_minutes,
                            template_type=selected_template if selected_template != "default" else None,
                            api_settings=api_settings
                        )

                        st.session_state.current_session = session
                        st.session_state.analysis_complete = True

                        # Update progress
                        progress_bar.progress(1.0)
                        status_text.success("✅ Analysis complete!")

                        # Show quick results
                        st.success("🎉 Analysis completed successfully!")

                        # Display summary
                        summary = st.session_state.engine.get_session_summary(session)
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Windows Processed", f"{session.successful_windows}/{session.total_windows}")
                        with col2:
                            st.metric("Success Rate", f"{session.successful_windows/session.total_windows*100:.1f}%")
                        with col3:
                            st.metric("Processing Time", f"{session.total_processing_time/1000:.1f}s")
                        with col4:
                            tokens = sum(r.tokens_used for r in session.recommendations if not r.recommendation.startswith('ERROR:'))
                            st.metric("Tokens Used", tokens)

                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")

        # Show progress if analyzing
        if hasattr(st.session_state, 'progress_value') and st.session_state.progress_value < 1.0 and st.session_state.progress_message:
            st.progress(st.session_state.progress_value)
            st.info(st.session_state.progress_message)

    # Templates Tab
    with tab2:
        st.header("📝 Prompt Templates")

        templates = get_available_templates()

        for template_name, description in templates.items():
            with st.expander(f"**{template_name.replace('_', ' ').title()}**"):
                st.write(description)

                # Show template content
                if st.button(f"View Template", key=f"view_{template_name}"):
                    prompt_manager = PromptManager()
                    template_content = prompt_manager.create_user_prompt_from_template(template_name)
                    st.code(template_content, language="markdown")

    # Results Tab
    with tab3:
        st.header("📈 Analysis Results")

        if st.session_state.current_session:
            session = st.session_state.current_session

            # Session overview
            st.subheader("Session Overview")
            col1, col2 = st.columns(2)

            with col1:
                st.json({
                    "Session ID": session.session_id,
                    "Timestamp": session.timestamp.isoformat(),
                    "Total Windows": session.total_windows,
                    "Successful Windows": session.successful_windows,
                    "Failed Windows": session.failed_windows
                })

            with col2:
                st.json({
                    "Processing Time": f"{session.total_processing_time/1000:.1f}s",
                    "Frame Count": session.frame_count,
                    "Video Duration": f"{session.video_duration:.1f}s",
                    "Success Rate": f"{session.successful_windows/session.total_windows*100:.1f}%"
                })

            # Recommendations
            st.subheader("Recommendations")

            for i, rec in enumerate(session.recommendations):
                with st.expander(f"Window {rec.window_index + 1} ({rec.window_start_time:.1f}s - {rec.window_end_time:.1f}s)"):
                    if rec.recommendation.startswith('ERROR:'):
                        st.error(rec.recommendation)
                    else:
                        st.write(rec.recommendation)

                        # Metadata
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Confidence", f"{rec.confidence:.2f}")
                        with col2:
                            st.metric("Processing", f"{rec.processing_time}ms")
                        with col3:
                            st.metric("Tokens", rec.tokens_used)
                        with col4:
                            st.metric("Tool Calls", rec.tool_calls)

                        if rec.search_results:
                            st.write("**Web Search Results:**")
                            for search in rec.search_results:
                                st.write(f"• {search.get('query', 'Unknown query')}")

            # Export options
            st.subheader("Export Results")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📄 Export as JSON"):
                    try:
                        output_path = st.session_state.engine.export_session(session, 'json')
                        st.success(f"✅ Exported to: {output_path}")
                    except Exception as e:
                        st.error(f"❌ Export failed: {e}")

            with col2:
                if st.button("📊 Export as CSV"):
                    try:
                        output_path = st.session_state.engine.export_session(session, 'csv')
                        st.success(f"✅ Exported to: {output_path}")
                    except Exception as e:
                        st.error(f"❌ Export failed: {e}")

        else:
            st.info("No analysis results available. Run an analysis first.")

    # System Test Tab
    with tab4:
        st.header("🔧 System Test")

        if st.button("Run Configuration Test"):
            with st.spinner("Testing system configuration..."):
                try:
                    engine = CoachingEngine()
                    test_results = engine.test_configuration()

                    if test_results['overall_status']:
                        st.success("✅ All tests passed!")
                    else:
                        st.error("❌ Some tests failed")

                    # Detailed results
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        api_result = test_results.get('api_test', {})
                        if api_result.get('success'):
                            st.success("🔗 API Connection: OK")
                            st.write(f"Model: {api_result.get('model', 'Unknown')}")
                            st.write(f"Time: {api_result.get('processing_time', 0)}ms")
                        else:
                            st.error("🔗 API Connection: Failed")
                            st.error(api_result.get('message', 'Unknown error'))

                    with col2:
                        frame_result = test_results.get('frame_processing_test', {})
                        if frame_result.get('success'):
                            st.success("📋 Frame Processing: OK")
                            st.write(f"Frames: {frame_result.get('frames_parsed', 0)}")
                            st.write(f"Windows: {frame_result.get('windows_created', 0)}")
                        else:
                            st.error("📋 Frame Processing: Failed")

                    with col3:
                        prompt_result = test_results.get('prompt_test', {})
                        if prompt_result.get('success'):
                            st.success("📝 Prompts: OK")
                            st.write(f"System: {prompt_result.get('system_prompt_length', 0)} chars")
                            st.write(f"User: {prompt_result.get('user_prompt_length', 0)} chars")
                        else:
                            st.error("📝 Prompts: Failed")

                    # Configuration details
                    with st.expander("Configuration Details"):
                        config_dict = Config.to_dict()
                        # Mask API key
                        if 'openai_api_key' in config_dict:
                            config_dict['openai_api_key'] = '***CONFIGURED***' if Config.OPENAI_API_KEY else 'Not set'
                        st.json(config_dict)

                except Exception as e:
                    st.error(f"❌ Test failed: {e}")

        # System information
        st.subheader("System Information")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Framework Version:** 2.0.0")
            st.write("**Streamlit Version:** " + st.__version__)
            st.write("**API Key Status:** " + ("✅ Configured" if Config.validate_api_key() else "❌ Not set"))

        with col2:
            st.write("**Default Model:** " + Config.DEFAULT_MODEL)
            st.write("**Default Interval:** " + f"{Config.DEFAULT_INTERVAL_MINUTES}min")
            st.write("**Output Directory:** " + Config.OUTPUT_DIR)

if __name__ == "__main__":
    main()