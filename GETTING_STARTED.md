# Getting Started with AI Performance Coaching Framework

This guide will help you set up and start using the AI Performance Coaching Framework to analyze screen recordings and generate productivity recommendations.

## Quick Setup

### 1. Prerequisites

- Python 3.8 or higher
- OpenAI API key with GPT-5 access
- Basic understanding of screen recording analysis

### 2. Installation

```bash
# Clone or download the framework
cd "Coach Project/ai-coaching-framework"

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 3. Verify Installation

Run the basic test suite to ensure everything is working:

```bash
python3 simple_test.py
```

You should see all tests pass with a green ✅ status.

## Using the Framework

### Option 1: Streamlit Web Interface (Recommended)

Launch the interactive web interface:

```bash
streamlit run app.py
```

This opens a browser interface where you can:
- Upload or paste frame description JSON
- Choose coaching focus templates
- Configure API settings
- View results and export data

### Option 2: Command Line Interface

Use the CLI for batch processing:

```bash
# Process frame descriptions
python cli.py process examples/sample_frames.json --interval 2 --template efficiency_focused

# Test system configuration
python cli.py test

# View available templates
python cli.py templates --list-templates

# Get help
python cli.py --help
```

## Input Format

The framework accepts frame descriptions in JSON format. Here's the basic structure:

```json
{
  "frames": [
    {
      "timestamp": 0.5,
      "description": "User opening Chrome browser"
    },
    {
      "timestamp": 30.2,
      "description": "Navigating to Gmail website"
    }
  ]
}
```

### Supported Formats

1. **Basic frames**: `{"frames": [...]}`
2. **Windows format**: `{"windows": [{"frames": [...]}]}`
3. **Intervals format**: `{"intervals": [{"frames": [...]}]}`
4. **Direct array**: `[{"timestamp": ..., "description": ...}]`

### Optional Fields

- `application`: Name of the application being used
- `window_title`: Title of the active window
- `confidence`: Confidence score of the frame detection
- `activities`: Array of detected activities

## Coaching Templates

Choose a template based on your analysis focus:

| Template | Description | Best For |
|----------|-------------|----------|
| `efficiency_focused` | Time waste elimination and speed improvements | General productivity analysis |
| `automation_focused` | Repetitive task automation opportunities | Process optimization |
| `learning_focused` | Skill development and knowledge gaps | Training and development |
| `meeting_focused` | Communication and collaboration optimization | Remote work analysis |
| `coding_focused` | Software development workflow improvements | Developer productivity |

## Configuration Options

### API Settings

- **Model**: Choose between GPT-5, GPT-4 Turbo, or GPT-4
- **Reasoning Effort**: Control GPT-5's reasoning depth (minimal/low/medium/high)
- **Temperature**: Adjust response creativity (0.0-2.0)
- **Max Tokens**: Set maximum response length

### Processing Settings

- **Chunking Interval**: Time window size (0.5-10 minutes)
- **Max Context Windows**: Previous windows to include for context
- **Retry Attempts**: API retry count for failed requests

## Example Workflow

1. **Record Screen Activity**: Use any screen recording tool to capture work sessions

2. **Extract Frame Descriptions**: Use AI tools or manual annotation to create frame descriptions with timestamps

3. **Prepare JSON**: Format frame descriptions according to the expected JSON structure

4. **Run Analysis**: Use either the web interface or CLI to process the data

5. **Review Recommendations**: Examine the generated productivity recommendations with evidence timestamps

6. **Export Results**: Save results as JSON or CSV for further analysis

## Sample Data

The framework includes sample data in the `examples/` directory:

- `sample_frames.json`: Email processing workflow (Gmail)
- `coding_session.json`: Software development session (VS Code)

Try these samples to understand the expected input format and see example recommendations.

## Troubleshooting

### Common Issues

**API Key Not Working**
```bash
# Check if your API key is set
python cli.py test
```

**Import Errors**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt
```

**Invalid Frame Data**
```bash
# Validate your JSON format
python cli.py validate your_frames.json
```

**Streamlit Not Starting**
```bash
# Try specifying port
streamlit run app.py --server.port 8502
```

### Getting Help

- Run `python cli.py --help` for CLI documentation
- Check the web interface's "System Test" tab for configuration issues
- Review the `tests/` directory for usage examples
- Examine `examples/` for proper JSON formatting

## Advanced Usage

### Custom Prompts

You can override the default system and user prompts:

```python
from src.coaching_engine import CoachingEngine

custom_prompts = {
    'system_prompt': 'Your custom system prompt...',
    'user_prompt': 'Your custom analysis instructions...'
}

engine = CoachingEngine()
session = engine.analyze_frames(
    frame_data=your_data,
    custom_prompts=custom_prompts
)
```

### API Settings Override

```python
api_settings = {
    'model_name': 'gpt-5',
    'reasoning_effort': 'high',
    'max_tokens': 6000,
    'temperature': 0.2
}

session = engine.analyze_frames(
    frame_data=your_data,
    api_settings=api_settings
)
```

### Batch Processing

Process multiple files programmatically:

```python
from pathlib import Path
from src.coaching_engine import CoachingEngine

engine = CoachingEngine()

for json_file in Path('data/').glob('*.json'):
    print(f"Processing {json_file.name}...")
    session = engine.analyze_frames(json_file)
    output_path = engine.export_session(session, 'json')
    print(f"Results saved to {output_path}")
```

## Next Steps

- Explore the different coaching templates to find the best fit for your use case
- Experiment with different chunking intervals to optimize analysis granularity
- Set up regular analysis sessions to track productivity improvements over time
- Integrate the framework into your existing workflow automation tools

For more detailed documentation, see the individual module docstrings and the `tests/` directory for comprehensive examples.