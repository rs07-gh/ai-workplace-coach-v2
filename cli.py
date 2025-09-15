#!/usr/bin/env python3
"""
CLI interface for the AI Performance Coaching Framework.
Provides command-line access to coaching analysis functionality.
"""

import sys
import json
import click
from pathlib import Path
from typing import Optional, Dict, Any

from src.coaching_engine import CoachingEngine
from src.config import Config
from src.utils import setup_logging
from src.prompt_manager import PromptManager

logger = setup_logging(__name__)

# Progress callback for CLI
def cli_progress_callback(message: str, progress: float) -> None:
    """Progress callback for CLI operations."""
    bar_length = 40
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    # Clear line and print progress
    sys.stdout.write(f'\r|{bar}| {progress*100:.1f}% - {message}')
    sys.stdout.flush()

    # New line when complete
    if progress >= 1.0:
        print()

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug: bool):
    """AI Performance Coaching Framework CLI."""
    if debug:
        Config.DEBUG_MODE = True
        logger.setLevel('DEBUG')

    # Validate API key
    if not Config.validate_api_key():
        click.echo(click.style("⚠️  OpenAI API key not configured!", fg='yellow'))
        click.echo("Set OPENAI_API_KEY environment variable or create .env file")
        sys.exit(1)

@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--interval', '-i', type=float, help='Chunking interval in minutes')
@click.option('--template', '-t',
              type=click.Choice(['efficiency_focused', 'automation_focused', 'learning_focused',
                               'meeting_focused', 'coding_focused']),
              help='Prompt template to use')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path')
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json',
              help='Output format')
@click.option('--model', type=str, help='OpenAI model to use')
@click.option('--reasoning-effort', type=click.Choice(['minimal', 'low', 'medium', 'high']),
              help='GPT-5 reasoning effort')
def process(
    input_file: Path,
    interval: Optional[float],
    template: Optional[str],
    output: Optional[Path],
    format: str,
    model: Optional[str],
    reasoning_effort: Optional[str]
):
    """Process frame descriptions and generate coaching recommendations."""
    try:
        click.echo(f"🚀 Processing frame descriptions from: {input_file}")

        # Setup API settings overrides
        api_settings = {}
        if model:
            api_settings['model_name'] = model
        if reasoning_effort:
            api_settings['reasoning_effort'] = reasoning_effort

        # Initialize engine with progress callback
        engine = CoachingEngine(progress_callback=cli_progress_callback)

        # Run analysis
        session = engine.analyze_frames(
            frame_data=input_file,
            interval_minutes=interval,
            template_type=template,
            api_settings=api_settings if api_settings else None
        )

        # Export results
        output_path = engine.export_session(session, output_format=format)

        # Show summary
        summary = engine.get_session_summary(session)
        click.echo("\n📊 Analysis Summary:")
        click.echo(f"   Session ID: {summary['session_id']}")
        click.echo(f"   Windows Processed: {summary['windows_processed']}")
        click.echo(f"   Success Rate: {summary['success_rate']}")
        click.echo(f"   Processing Time: {summary['total_processing_time']}")
        click.echo(f"   Tokens Used: {summary['total_tokens_used']}")
        click.echo(f"   Output File: {output_path}")

        if session.failed_windows > 0:
            click.echo(click.style(f"⚠️  {session.failed_windows} windows failed processing", fg='yellow'))

        click.echo(click.style("✅ Analysis complete!", fg='green'))

    except Exception as error:
        click.echo(click.style(f"❌ Analysis failed: {error}", fg='red'))
        sys.exit(1)

@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
def validate(input_file: Path):
    """Validate frame description format."""
    try:
        click.echo(f"🔍 Validating frame descriptions: {input_file}")

        # Load and validate
        with open(input_file, 'r', encoding='utf-8') as f:
            frame_data = f.read()

        from src.frame_processor import FrameProcessor
        processor = FrameProcessor()

        validation_result = processor.validate_frame_data(frame_data)

        if validation_result['valid']:
            click.echo(click.style("✅ Frame data is valid!", fg='green'))
            click.echo(f"   Frames found: {validation_result['frame_count']}")
            click.echo(f"   Has timestamps: {validation_result['has_timestamps']}")
            click.echo(f"   Has descriptions: {validation_result['has_descriptions']}")
        else:
            click.echo(click.style("❌ Frame data validation failed:", fg='red'))
            for error in validation_result['errors']:
                click.echo(f"   - {error}")
            sys.exit(1)

    except Exception as error:
        click.echo(click.style(f"❌ Validation failed: {error}", fg='red'))
        sys.exit(1)

@cli.command()
def test():
    """Test system configuration and API connectivity."""
    try:
        click.echo("🔧 Testing coaching framework configuration...")

        engine = CoachingEngine()
        test_results = engine.test_configuration()

        if test_results['overall_status']:
            click.echo(click.style("✅ All tests passed!", fg='green'))
        else:
            click.echo(click.style("❌ Some tests failed:", fg='red'))

        # Show detailed results
        if 'api_test' in test_results:
            api_result = test_results['api_test']
            status = "✅" if api_result['success'] else "❌"
            click.echo(f"   {status} API Connection: {api_result.get('message', 'Unknown')}")

        if 'frame_processing_test' in test_results:
            frame_result = test_results['frame_processing_test']
            status = "✅" if frame_result['success'] else "❌"
            click.echo(f"   {status} Frame Processing: {frame_result.get('frames_parsed', 'Error')}")

        if 'prompt_test' in test_results:
            prompt_result = test_results['prompt_test']
            status = "✅" if prompt_result['success'] else "❌"
            click.echo(f"   {status} Prompt Management: Ready")

        if not test_results['overall_status']:
            sys.exit(1)

    except Exception as error:
        click.echo(click.style(f"❌ Test failed: {error}", fg='red'))
        sys.exit(1)

@cli.command()
@click.option('--list-templates', is_flag=True, help='List available templates')
@click.option('--template', type=str, help='Show specific template content')
def templates(list_templates: bool, template: str):
    """Manage prompt templates."""
    try:
        prompt_manager = PromptManager()

        if list_templates:
            click.echo("📝 Available prompt templates:")
            templates = prompt_manager.get_available_templates()
            for name, description in templates.items():
                click.echo(f"   {name}: {description}")

        elif template:
            if template in prompt_manager.get_available_templates():
                prompt_content = prompt_manager.create_user_prompt_from_template(template)
                click.echo(f"📝 Template: {template}")
                click.echo("─" * 80)
                click.echo(prompt_content)
                click.echo("─" * 80)
            else:
                click.echo(click.style(f"❌ Template '{template}' not found", fg='red'))
                click.echo("Use --list-templates to see available templates")
                sys.exit(1)

        else:
            click.echo("Use --list-templates to see available templates")
            click.echo("Use --template <name> to view template content")

    except Exception as error:
        click.echo(click.style(f"❌ Template command failed: {error}", fg='red'))
        sys.exit(1)

@cli.command()
@click.option('--set-model', type=str, help='Set default model')
@click.option('--set-interval', type=float, help='Set default interval (minutes)')
@click.option('--set-reasoning', type=click.Choice(['minimal', 'low', 'medium', 'high']),
              help='Set default reasoning effort')
@click.option('--show', is_flag=True, help='Show current configuration')
def config(set_model: str, set_interval: float, set_reasoning: str, show: bool):
    """Manage configuration settings."""
    try:
        if show:
            click.echo("⚙️  Current Configuration:")
            config_dict = Config.to_dict()
            for key, value in config_dict.items():
                if key == 'openai_api_key':
                    value = '***CONFIGURED***' if Config.OPENAI_API_KEY else 'Not set'
                click.echo(f"   {key}: {value}")

        changes_made = False

        if set_model:
            Config.DEFAULT_MODEL = set_model
            click.echo(f"✅ Set model to: {set_model}")
            changes_made = True

        if set_interval:
            Config.DEFAULT_INTERVAL_MINUTES = set_interval
            click.echo(f"✅ Set interval to: {set_interval} minutes")
            changes_made = True

        if set_reasoning:
            Config.REASONING_EFFORT = set_reasoning
            click.echo(f"✅ Set reasoning effort to: {set_reasoning}")
            changes_made = True

        if changes_made:
            click.echo("💾 Changes will apply to new sessions")

        if not any([show, set_model, set_interval, set_reasoning]):
            click.echo("Use --show to view current configuration")
            click.echo("Use --set-* options to modify settings")

    except Exception as error:
        click.echo(click.style(f"❌ Config command failed: {error}", fg='red'))
        sys.exit(1)

@cli.command()
@click.argument('session_file', type=click.Path(exists=True, path_type=Path))
def summary(session_file: Path):
    """Show summary of a previous analysis session."""
    try:
        click.echo(f"📊 Loading session summary from: {session_file}")

        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        if 'session_metadata' not in session_data:
            click.echo(click.style("❌ Invalid session file format", fg='red'))
            sys.exit(1)

        metadata = session_data['session_metadata']

        click.echo("📈 Session Summary:")
        click.echo(f"   Session ID: {metadata['session_id']}")
        click.echo(f"   Timestamp: {metadata['timestamp']}")
        click.echo(f"   Windows: {metadata['total_windows']}")
        click.echo(f"   Success Rate: {metadata['successful_windows']}/{metadata['total_windows']} ({metadata['success_rate']:.1%})")
        click.echo(f"   Processing Time: {metadata['total_processing_time_ms']/1000:.1f}s")
        click.echo(f"   Video Duration: {metadata['video_duration_seconds']:.1f}s")
        click.echo(f"   Frames: {metadata['frame_count']}")

        # Show recommendations summary
        recommendations = session_data.get('recommendations', [])
        successful_recs = [r for r in recommendations if not r.get('has_error', False)]

        if successful_recs:
            avg_confidence = sum(r.get('confidence', 0) for r in successful_recs) / len(successful_recs)
            total_tokens = sum(r.get('tokens_used', 0) for r in successful_recs)

            click.echo(f"   Average Confidence: {avg_confidence:.2f}")
            click.echo(f"   Total Tokens: {total_tokens}")

    except Exception as error:
        click.echo(click.style(f"❌ Summary failed: {error}", fg='red'))
        sys.exit(1)

if __name__ == '__main__':
    cli()