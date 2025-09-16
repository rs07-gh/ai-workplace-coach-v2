"""
AI Coaching Framework v2 - Enhanced Streamlit Application
Features session management, GPT-5 integration, batch processing, and context continuity.
"""

import asyncio
import os
import uuid
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import streamlit as st
from dotenv import load_dotenv

# Import v2 components
from src.database import DatabaseManager, GPTConfig, ProcessingConfig, SessionStatus, WindowStatus
from src.enhanced_window_processor import EnhancedWindowProcessor
from src.context_manager import ContextManager
from src.gpt5_client import GPT5Client
from src.batch_processor import BatchProcessor, BatchJobConfig


# Page configuration
st.set_page_config(
    page_title="AI Coaching Framework v2",
    page_icon="🧠",
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

.warning-message {
    background: #fff3cd;
    color: #856404;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #ffeaa7;
}

.error-message {
    background: #f8d7da;
    color: #721c24;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #f1b0b7;
}

.info-message {
    background: #d1ecf1;
    color: #0c5460;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border: 1px solid #b8daff;
}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'db_manager' not in st.session_state:
        db_path = Path("coaching_sessions.db")
        st.session_state.db_manager = DatabaseManager(str(db_path))

    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None

    if 'processing_active' not in st.session_state:
        st.session_state.processing_active = False

    if 'processing_progress' not in st.session_state:
        st.session_state.processing_progress = {'current': 0, 'total': 0, 'status': ''}

    if 'batch_processor' not in st.session_state:
        st.session_state.batch_processor = None

    if 'active_batch_jobs' not in st.session_state:
        st.session_state.active_batch_jobs = {}


def load_default_system_prompt() -> str:
    """Load the default system prompt from file."""
    prompt_file = Path("src/prompts/klarity_coach_system_prompt.md")

    if prompt_file.exists():
        return prompt_file.read_text(encoding='utf-8')
    else:
        return """You are Klarity Coach, an AI performance coach specializing in workflow optimization.

Analyze frame descriptions to identify inefficiencies and provide actionable recommendations for improving user productivity.

Focus on:
1. Application usage patterns
2. Keyboard shortcuts and automation opportunities
3. Workflow optimization techniques
4. Time-saving strategies

Provide specific, implementable recommendations with clear steps."""


def render_sidebar_config():
    """Render the sidebar with API and processing configuration."""
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Configuration
        with st.expander("🔑 API Settings", expanded=True):
            # API key is now handled securely via Streamlit secrets (backend-only)
            try:
                api_key = st.secrets["OPENAI_API_KEY"]
                os.environ["OPENAI_API_KEY"] = api_key
                st.success("🔑 API Key configured securely via backend secrets")
            except KeyError:
                st.error("🔑 API Key not found in secrets. Please contact administrator.")
                st.info("💡 API keys are now managed securely on the backend for security.")

        # Processing Configuration
        with st.expander("🛠️ Processing Settings"):
            window_seconds = st.slider(
                "Window Duration (seconds)",
                min_value=10,
                max_value=60,
                value=30,
                help="Duration of each processing window"
            )

            enable_web_search = st.checkbox(
                "Enable Web Search",
                value=True,
                help="Allow GPT-5 to search for optimization techniques"
            )

            enable_tool_calling = st.checkbox(
                "Enable Tool Calling",
                value=True,
                help="Allow GPT-5 to use analysis tools"
            )

        # GPT-5 Model Configuration
        with st.expander("🤖 GPT-5 Settings"):
            model = st.selectbox(
                "Model",
                options=["gpt-5", "gpt-5-mini", "gpt-5-nano"],
                index=0,  # Default to gpt-5
                help="Choose GPT-5 model variant"
            )

            reasoning_effort = st.selectbox(
                "Reasoning Effort",
                options=["minimal", "low", "medium", "high"],
                index=2,
                help="Controls GPT-5's thinking time"
            )

            verbosity = st.selectbox(
                "Verbosity",
                options=["minimal", "low", "medium", "high"],
                index=2,
                help="Controls response length"
            )

            # Note: GPT-5 doesn't use temperature parameter
            st.info("💡 GPT-5 models use reasoning effort instead of temperature")

        return {
            'api_key': api_key,
            'processing_config': ProcessingConfig(
                window_seconds=window_seconds,
                enable_web_search=enable_web_search,
                enable_tool_calling=enable_tool_calling
            ),
            'gpt_config': GPTConfig(
                model=model,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity
                # Note: temperature removed - GPT-5 doesn't use this parameter
            )
        }


def render_session_management():
    """Render session creation and management interface."""
    st.header("📁 Session Management")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Create new session
        with st.expander("➕ Create New Session", expanded=True):
            session_name = st.text_input("Session Name", placeholder="e.g., Excel Analysis Session")

            uploaded_file = st.file_uploader(
                "Upload Frame Descriptions JSON",
                type=['json'],
                help="Upload JSON file containing frame descriptions from Step 1 processing"
            )

            if uploaded_file:
                # Show file preview
                try:
                    file_content = json.loads(uploaded_file.read())
                    uploaded_file.seek(0)  # Reset file pointer

                    st.info(f"📄 File: {uploaded_file.name}")
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Duration", f"{file_content.get('duration_seconds', 0):.1f}s")
                    with col_b:
                        st.metric("Windows", len(file_content.get('windows', [])))
                    with col_c:
                        st.metric("Model Used", file_content.get('model', 'Unknown'))
                except:
                    st.error("Invalid JSON file format")

            if st.button("🚀 Create Session", type="primary", disabled=not (session_name and uploaded_file)):
                if session_name and uploaded_file:
                    create_new_session(session_name, uploaded_file)

    with col2:
        # Load existing session
        with st.expander("📂 Load Existing Session"):
            sessions = st.session_state.db_manager.list_sessions()

            if sessions:
                for session in sessions[:5]:  # Show last 5 sessions
                    with st.container():
                        st.write(f"**{session['name'][:30]}...**" if len(session['name']) > 30 else f"**{session['name']}**")
                        col_a, col_b = st.columns([2, 1])
                        with col_a:
                            st.caption(f"Status: {session['status'].title()}")
                        with col_b:
                            if st.button("Load", key=f"load_{session['id']}", help=f"Load {session['name']}"):
                                load_existing_session(session['id'])
                        st.divider()
            else:
                st.info("No existing sessions found")


def create_new_session(session_name: str, uploaded_file):
    """Create a new processing session."""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temp_file:
            temp_file.write(uploaded_file.read())
            temp_path = temp_file.name

        # Validate JSON structure
        processor = EnhancedWindowProcessor()
        is_valid, message = processor.validate_json_structure(temp_path)

        if not is_valid:
            st.error(f"❌ Invalid JSON structure: {message}")
            os.remove(temp_path)
            return

        # Create session
        session_id = str(uuid.uuid4())
        config = st.session_state.get('config', {})

        success = st.session_state.db_manager.create_session(
            session_id=session_id,
            name=session_name,
            gpt_config=config.get('gpt_config', GPTConfig()),
            processing_config=config.get('processing_config', ProcessingConfig()),
            input_file_path=temp_path
        )

        if success:
            st.session_state.current_session_id = session_id
            st.success(f"✅ Session created: {session_name}")
            st.rerun()
        else:
            st.error("❌ Failed to create session")

        # Clean up temp file
        os.remove(temp_path)

    except Exception as e:
        st.error(f"❌ Error creating session: {str(e)}")


def load_existing_session(session_id: str):
    """Load an existing session."""
    st.session_state.current_session_id = session_id
    st.success("✅ Session loaded")
    st.rerun()


def render_system_prompt_editor():
    """Render the system prompt editor."""
    st.header("✏️ System Prompt Editor")

    # Load default or saved prompt
    default_prompt = load_default_system_prompt()

    # Rich text editor using text area
    prompt_text = st.text_area(
        "System Prompt",
        value=default_prompt,
        height=400,
        help="Edit the system prompt for GPT-5 analysis"
    )

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Template"):
            save_prompt_template(prompt_text)

    with col2:
        if st.button("🔄 Reset to Default"):
            st.rerun()

    # Store prompt in session state
    if 'processing_config' not in st.session_state:
        st.session_state.processing_config = ProcessingConfig()

    st.session_state.processing_config.system_prompt = prompt_text

    return prompt_text


def save_prompt_template(prompt_text: str):
    """Save system prompt as a template."""
    templates_dir = Path("src/prompts")
    templates_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    template_path = templates_dir / f"custom_prompt_{timestamp}.md"

    template_path.write_text(prompt_text, encoding='utf-8')
    st.success(f"✅ Template saved: {template_path.name}")


def render_processing_interface():
    """Render the processing interface for active sessions."""
    if not st.session_state.current_session_id:
        st.warning("⚠️ Please create or load a session first")
        return

    session = st.session_state.db_manager.get_session(st.session_state.current_session_id)
    if not session:
        st.error("❌ Session not found")
        return

    st.header(f"🚀 Processing: {session['name']}")

    # Session status dashboard
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_color = {
            'created': '🟡',
            'processing': '🔵',
            'paused': '🟠',
            'completed': '🟢',
            'failed': '🔴'
        }
        st.metric("Status", f"{status_color.get(session['status'], '⚪')} {session['status'].title()}")

    with col2:
        st.metric("Total Windows", session.get('total_windows', 0))

    with col3:
        st.metric("Completed", session.get('completed_windows', 0))

    with col4:
        if session.get('total_windows', 0) > 0:
            progress = (session.get('completed_windows', 0) / session['total_windows']) * 100
            st.metric("Progress", f"{progress:.1f}%")

    # Processing controls
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if session['status'] in ['created', 'paused']:
            if st.button("▶️ Start Processing", type="primary"):
                start_processing()

    with col2:
        if session['status'] == 'processing':
            if st.button("⏸️ Pause Processing"):
                pause_processing()

    with col3:
        if session['status'] in ['processing', 'paused']:
            if st.button("⏹️ Stop Processing"):
                stop_processing()

    with col4:
        if st.button("🔄 Refresh Status"):
            st.rerun()

    # Real-time progress display
    if st.session_state.processing_active:
        render_processing_progress()

    # Session details
    with st.expander("📊 Session Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Created:** {session['created_at']}")
            st.write(f"**Model:** {session['gpt_config'].model}")
            st.write(f"**Window Size:** {session['processing_config'].window_seconds}s")
        with col2:
            st.write(f"**Updated:** {session['updated_at']}")
            st.write(f"**Reasoning:** {session['gpt_config'].reasoning_effort}")
            st.write(f"**Verbosity:** {session['gpt_config'].verbosity}")


def start_processing():
    """Start processing the current session."""
    if not st.session_state.current_session_id:
        return

    st.session_state.processing_active = True
    st.session_state.db_manager.update_session_status(
        st.session_state.current_session_id,
        SessionStatus.PROCESSING
    )

    # Start processing using threading instead of asyncio for Streamlit compatibility
    import threading
    processing_thread = threading.Thread(target=process_session_sync)
    processing_thread.daemon = True
    processing_thread.start()

    st.success("🚀 Processing started!")
    st.rerun()


def pause_processing():
    """Pause the current processing session."""
    st.session_state.processing_active = False
    st.session_state.db_manager.update_session_status(
        st.session_state.current_session_id,
        SessionStatus.PAUSED
    )
    st.info("⏸️ Processing paused")
    st.rerun()


def stop_processing():
    """Stop the current processing session."""
    st.session_state.processing_active = False
    st.session_state.db_manager.update_session_status(
        st.session_state.current_session_id,
        SessionStatus.FAILED
    )
    st.warning("⏹️ Processing stopped")
    st.rerun()


async def process_session_async():
    """Process the session asynchronously."""
    try:
        session_id = st.session_state.current_session_id
        session = st.session_state.db_manager.get_session(session_id)

        if not session:
            return

        # Initialize processors
        window_processor = EnhancedWindowProcessor(
            window_seconds=session['processing_config'].window_seconds
        )
        context_manager = ContextManager(st.session_state.db_manager)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            st.error("❌ OpenAI API Key not configured")
            return

        gpt5_client = GPT5Client(api_key)

        # Load and process windows
        frame_descriptions, metadata = window_processor.load_frame_descriptions_from_json(
            session['input_file_path']
        )
        windows = window_processor.create_windows_from_frames(frame_descriptions)

        # Update session with total windows
        st.session_state.db_manager.update_session_status(
            session_id, SessionStatus.PROCESSING, completed_windows=0
        )

        # Process each window
        for i, window in enumerate(windows, 1):
            if not st.session_state.processing_active:
                break

            # Update progress
            st.session_state.processing_progress = {
                'current': i,
                'total': len(windows),
                'status': f'Processing window {i}/{len(windows)}'
            }

            # Create window in database
            window_id = f"{session_id}_window_{i}"
            st.session_state.db_manager.create_window(
                window_id=window_id,
                session_id=session_id,
                window_number=i,
                start_time=window.start_time,
                end_time=window.end_time,
                input_data=window.to_dict()
            )

            # Build context for this window
            context_prompt = context_manager.build_context_for_window(
                session_id, i, window
            )

            # Analyze with GPT-5
            try:
                result = await gpt5_client.analyze_window_with_context(
                    system_prompt=session['processing_config'].system_prompt,
                    context_prompt=context_prompt,
                    window_data=window.to_dict(),
                    config=session['gpt_config']
                )

                # Save results
                st.session_state.db_manager.update_window_status(
                    window_id=window_id,
                    status=WindowStatus.COMPLETED,
                    output_data=result.to_dict(),
                    processing_time=result.processing_time_seconds
                )

                # Save context and recommendations
                context_manager.save_window_context(
                    session_id=session_id,
                    window_number=i,
                    window_context=window_processor.extract_window_context(window),
                    analysis_result=result.content
                )

                # Update session progress
                st.session_state.db_manager.update_session_status(
                    session_id, SessionStatus.PROCESSING, completed_windows=i
                )

            except Exception as e:
                st.error(f"❌ Error processing window {i}: {e}")
                st.session_state.db_manager.update_window_status(
                    window_id=window_id,
                    status=WindowStatus.FAILED,
                    error_message=str(e)
                )

        # Mark session as completed
        if st.session_state.processing_active:
            st.session_state.db_manager.update_session_status(
                session_id, SessionStatus.COMPLETED, completed_windows=len(windows)
            )
            st.session_state.processing_active = False

    except Exception as e:
        st.error(f"❌ Error in session processing: {e}")
        st.session_state.processing_active = False


def process_session_sync():
    """Process the session synchronously for Streamlit compatibility."""
    import asyncio

    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(process_session_async())
    finally:
        loop.close()


def render_processing_progress():
    """Render real-time processing progress."""
    progress = st.session_state.processing_progress

    if progress['total'] > 0:
        progress_pct = progress['current'] / progress['total']
        st.progress(progress_pct)
        st.write(f"**{progress['status']}**")
        st.write(f"Progress: {progress['current']}/{progress['total']} windows")


def render_results_interface():
    """Render the results and recommendations interface."""
    if not st.session_state.current_session_id:
        st.warning("⚠️ Please select a session to view results")
        return

    st.header("📊 Analysis Results")

    session_id = st.session_state.current_session_id

    # Get session recommendations
    recommendations = st.session_state.db_manager.get_session_recommendations(session_id)

    if not recommendations:
        st.info("💭 No recommendations available yet. Process the session first.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Recommendations", len(recommendations))

    with col2:
        categories = set(rec['category'] for rec in recommendations)
        st.metric("Categories", len(categories))

    with col3:
        avg_confidence = sum(rec.get('confidence_score', 0) for rec in recommendations) / len(recommendations)
        st.metric("Avg Confidence", f"{avg_confidence:.2f}")

    with col4:
        high_confidence = len([rec for rec in recommendations if rec.get('confidence_score', 0) > 0.8])
        st.metric("High Confidence", high_confidence)

    # Category filter
    categories = ['All'] + list(set(rec['category'] for rec in recommendations))
    selected_category = st.selectbox("Filter by Category", categories)

    # Filter recommendations
    filtered_recs = recommendations
    if selected_category != 'All':
        filtered_recs = [rec for rec in recommendations if rec['category'] == selected_category]

    # Recommendations display
    st.subheader(f"🎯 Recommendations ({len(filtered_recs)})")

    for i, rec in enumerate(filtered_recs, 1):
        confidence_color = "🟢" if rec.get('confidence_score', 0) > 0.8 else "🟡" if rec.get('confidence_score', 0) > 0.6 else "🟠"

        with st.expander(f"{confidence_color} Recommendation {i}: {rec['recommendation_text'][:60]}..."):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write("**Full Recommendation:**")
                st.write(rec['recommendation_text'])

                if rec.get('implementation_steps'):
                    st.write("**Implementation Steps:**")
                    for step in rec['implementation_steps']:
                        st.write(f"• {step}")

                if rec.get('expected_impact'):
                    st.write(f"**Expected Impact:** {rec['expected_impact']}")

            with col2:
                st.metric("Confidence", f"{rec.get('confidence_score', 0):.2f}")
                st.write(f"**Category:** {rec['category'].title()}")
                st.write(f"**Window:** {rec['window_number']}")

    # Export options
    st.subheader("📤 Export Results")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Export as Markdown"):
            export_results_markdown(filtered_recs)

    with col2:
        if st.button("📝 Export as TXT"):
            export_results_txt(filtered_recs)


def export_results_markdown(recommendations: List[Dict[str, Any]]):
    """Export recommendations as Markdown."""
    markdown_content = generate_markdown_export(recommendations)

    st.download_button(
        label="📥 Download Markdown File",
        data=markdown_content,
        file_name=f"coaching_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown"
    )


def export_results_txt(recommendations: List[Dict[str, Any]]):
    """Export recommendations as plain text."""
    txt_content = generate_txt_export(recommendations)

    st.download_button(
        label="📥 Download TXT File",
        data=txt_content,
        file_name=f"coaching_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )


def generate_markdown_export(recommendations: List[Dict[str, Any]]) -> str:
    """Generate Markdown formatted export."""
    lines = [
        "# AI Coaching Analysis Report",
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"## Summary",
        f"Total Recommendations: {len(recommendations)}",
        "",
        "## Recommendations",
        ""
    ]

    for i, rec in enumerate(recommendations, 1):
        lines.extend([
            f"### {i}. {rec['recommendation_text'][:100]}...",
            f"**Category:** {rec['category'].title()}",
            f"**Confidence Score:** {rec.get('confidence_score', 0):.2f}",
            f"**Window:** {rec['window_number']}",
            "",
            f"**Full Recommendation:**",
            rec['recommendation_text'],
            ""
        ])

        if rec.get('implementation_steps'):
            lines.append("**Implementation Steps:**")
            for step in rec['implementation_steps']:
                lines.append(f"- {step}")
            lines.append("")

        if rec.get('expected_impact'):
            lines.extend([
                f"**Expected Impact:** {rec['expected_impact']}",
                ""
            ])

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_txt_export(recommendations: List[Dict[str, Any]]) -> str:
    """Generate plain text formatted export."""
    lines = [
        "AI COACHING ANALYSIS REPORT",
        "=" * 50,
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"SUMMARY",
        f"Total Recommendations: {len(recommendations)}",
        "",
        "RECOMMENDATIONS",
        "-" * 20,
        ""
    ]

    for i, rec in enumerate(recommendations, 1):
        lines.extend([
            f"{i}. {rec['recommendation_text']}",
            f"   Category: {rec['category'].title()}",
            f"   Confidence: {rec.get('confidence_score', 0):.2f}",
            f"   Window: {rec['window_number']}",
            ""
        ])

        if rec.get('expected_impact'):
            lines.extend([
                f"   Expected Impact: {rec['expected_impact']}",
                ""
            ])

        lines.append("-" * 50)
        lines.append("")

    return "\n".join(lines)


def render_batch_processing_interface():
    """Render the batch processing interface."""
    st.header("📦 Batch Processing")

    # Initialize batch processor if needed
    if st.session_state.batch_processor is None and os.environ.get("OPENAI_API_KEY"):
        st.session_state.batch_processor = BatchProcessor(
            st.session_state.db_manager,
            os.environ.get("OPENAI_API_KEY")
        )

    if st.session_state.batch_processor is None:
        st.warning("⚠️ Please configure an API key to use batch processing")
        return

    # Batch job creation
    with st.expander("➕ Create New Batch Job", expanded=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            batch_name = st.text_input("Batch Job Name", placeholder="e.g., Weekly Analysis Batch")

            # File uploader for multiple files
            uploaded_files = st.file_uploader(
                "Upload Frame Description JSON Files",
                type=['json'],
                accept_multiple_files=True,
                help="Upload multiple JSON files for batch processing"
            )

            # Processing configuration
            with st.expander("⚙️ Batch Configuration"):
                max_concurrent = st.slider("Max Concurrent Sessions", 1, 5, 3)
                max_retries = st.slider("Max Retries per Window", 0, 3, 2)

        with col2:
            if uploaded_files and batch_name:
                st.info(f"📁 {len(uploaded_files)} files selected")

                # Estimate processing time and cost
                if st.button("📊 Estimate Cost & Time"):
                    estimate_batch_job(uploaded_files)

                if st.button("🚀 Start Batch Job", type="primary"):
                    start_batch_job(batch_name, uploaded_files, max_concurrent, max_retries)

    # Active batch jobs monitoring
    st.subheader("🔄 Active Batch Jobs")

    active_jobs = st.session_state.batch_processor.get_all_active_jobs()

    if not active_jobs:
        st.info("💭 No active batch jobs")
    else:
        for job_progress in active_jobs:
            render_batch_job_status(job_progress)


def estimate_batch_job(uploaded_files):
    """Estimate processing time and cost for a batch job."""
    try:
        # Save files temporarily
        temp_paths = []
        for file in uploaded_files:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temp_file:
                temp_file.write(file.read())
                temp_paths.append(temp_file.name)

        # Get configuration
        config = st.session_state.get('config', {})
        processing_config = config.get('processing_config', ProcessingConfig())
        gpt_config = config.get('gpt_config', GPTConfig())

        # Make sure system prompt is included
        if hasattr(st.session_state, 'processing_config') and st.session_state.processing_config.system_prompt:
            processing_config.system_prompt = st.session_state.processing_config.system_prompt

        # Get estimate
        estimate = asyncio.run(
            st.session_state.batch_processor.estimate_batch_processing_time(
                temp_paths, processing_config, gpt_config
            )
        )

        # Display estimate
        st.success("📊 Batch Processing Estimate")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sessions", estimate['total_sessions'])
        with col2:
            st.metric("Total Windows", estimate['total_windows'])
        with col3:
            st.metric("Est. Time (min)", f"{estimate['estimated_processing_time_minutes']:.1f}")
        with col4:
            st.metric("Est. Cost (USD)", f"${estimate['estimated_cost_usd']:.2f}")

        # Clean up temp files
        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        st.error(f"❌ Error estimating batch job: {str(e)}")


def start_batch_job(batch_name: str, uploaded_files, max_concurrent: int, max_retries: int):
    """Start a new batch processing job."""
    try:
        # Save files temporarily
        temp_paths = []
        for file in uploaded_files:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temp_file:
                temp_file.write(file.read())
                temp_paths.append(temp_file.name)

        # Get configuration
        config = st.session_state.get('config', {})
        processing_config = config.get('processing_config', ProcessingConfig())
        gpt_config = config.get('gpt_config', GPTConfig())

        # Make sure system prompt is included
        if hasattr(st.session_state, 'processing_config') and st.session_state.processing_config.system_prompt:
            processing_config.system_prompt = st.session_state.processing_config.system_prompt

        # Create batch job config
        batch_config = BatchJobConfig(
            name=batch_name,
            input_files=temp_paths,
            gpt_config=gpt_config,
            processing_config=processing_config,
            max_concurrent_sessions=max_concurrent,
            max_retries_per_window=max_retries
        )

        # Start batch job
        def progress_callback(progress):
            st.session_state.active_batch_jobs[progress.job_id] = progress

        job_id = asyncio.run(
            st.session_state.batch_processor.start_batch_job(
                batch_config, progress_callback
            )
        )

        st.success(f"✅ Batch job started: {batch_name} (ID: {job_id[:8]}...)")
        st.rerun()

    except Exception as e:
        st.error(f"❌ Error starting batch job: {str(e)}")


def render_batch_job_status(job_progress):
    """Render the status of a single batch job."""
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            st.write(f"**Job ID:** {job_progress.job_id[:8]}...")
            st.write(f"**Status:** {job_progress.overall_status.title()}")

        with col2:
            st.metric("Progress", f"{job_progress.completion_percentage:.1f}%")

        with col3:
            st.metric("Completed", f"{job_progress.completed_sessions}/{job_progress.total_sessions}")

        with col4:
            if job_progress.overall_status == "processing":
                if st.button(f"⏹️ Cancel", key=f"cancel_{job_progress.job_id}"):
                    st.session_state.batch_processor.cancel_batch_job(job_progress.job_id)
                    st.rerun()

        # Progress bar
        if job_progress.total_sessions > 0:
            progress_pct = job_progress.completion_percentage / 100
            st.progress(progress_pct)

        # Active sessions
        if job_progress.active_sessions:
            st.write(f"**Active Sessions:** {', '.join([s[:8] + '...' for s in job_progress.active_sessions])}")

        st.divider()


def main():
    """Main Streamlit application."""
    # Load environment variables
    load_dotenv()

    # Initialize session state
    init_session_state()

    # Header
    st.markdown('<h1 class="main-header">🧠 AI Coaching Framework v2</h1>', unsafe_allow_html=True)
    st.markdown("**Enhanced with Session Management, GPT-5 Integration & Batch Processing**")

    # Render sidebar configuration
    config = render_sidebar_config()
    st.session_state.config = config

    if not config['api_key']:
        st.error("🚨 **Please provide an OpenAI API Key in the sidebar to continue.**")
        st.markdown("""
        ### 🔑 Getting Started:
        1. Enter your OpenAI API key in the sidebar
        2. Create a new session or load an existing one
        3. Configure your system prompt
        4. Start processing your frame descriptions
        """)
        return

    # Main interface tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📁 Session Management",
        "✏️ System Prompt",
        "🚀 Processing",
        "📊 Results",
        "📦 Batch Processing"
    ])

    with tab1:
        render_session_management()

    with tab2:
        render_system_prompt_editor()

    with tab3:
        render_processing_interface()

    with tab4:
        render_results_interface()

    with tab5:
        render_batch_processing_interface()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        AI Coaching Framework v2 | Enhanced with GPT-5 & Session Management
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()