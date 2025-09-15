# AI Performance Coaching Framework

A comprehensive framework for analyzing screen recordings and generating evidence-based productivity recommendations using GPT-5 with web search capabilities.

## Features

- **Rolling Window Analysis**: Process frame descriptions in configurable time chunks with context carryover
- **GPT-5 Integration**: Advanced reasoning with web search tools for research-enhanced recommendations
- **Template-Based Prompts**: Multiple coaching focus areas (efficiency, automation, learning, etc.)
- **Flexible Input Formats**: Support for various JSON frame description structures
- **Streamlit UI**: Interactive web interface for easy use
- **CLI Interface**: Command-line tool for batch processing
- **Comprehensive Logging**: Detailed progress tracking and error handling

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Run Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. **Or use CLI:**
   ```bash
   python cli.py process --input frames.json --interval 2
   ```

## Architecture

- `app.py` - Streamlit web interface
- `cli.py` - Command-line interface
- `src/` - Core framework modules
  - `api_client.py` - OpenAI GPT-5 integration with tools
  - `frame_processor.py` - Frame parsing and chunking
  - `prompt_manager.py` - System and user prompt templates
  - `window_manager.py` - Context building and summarization
  - `coaching_engine.py` - Main analysis orchestration
  - `config.py` - Configuration management
  - `utils.py` - Helper functions

## Usage

### Frame Description Format

The framework accepts multiple JSON formats:

```json
{
  "frames": [
    {
      "timestamp": 0.5,
      "description": "User opening Chrome browser"
    },
    {
      "timestamp": 2.1,
      "description": "Typing in search bar"
    }
  ]
}
```

### Template Types

- **efficiency_focused**: Time waste elimination and speed improvements
- **automation_focused**: Repetitive task automation opportunities
- **learning_focused**: Skill development and knowledge gaps
- **meeting_focused**: Communication and collaboration optimization
- **coding_focused**: Software development workflow improvements

## Configuration

Edit `.env` file to customize:
- Model settings (GPT-5, reasoning effort, temperature)
- Processing parameters (interval, context windows)
- Output preferences (directory, logging level)