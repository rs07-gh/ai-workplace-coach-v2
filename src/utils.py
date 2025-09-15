"""
Utility functions for the AI Coaching Framework.
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from .config import Config

def setup_logging(name: str) -> logging.Logger:
    """Set up logging for a module."""

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO if Config.ENABLE_LOGGING else logging.WARNING)

    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    if Config.ENABLE_LOGGING:
        log_file = Path(Config.LOGS_DIR) / f"coaching_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(console_formatter)
        logger.addHandler(file_handler)

    return logger

def safe_json_parse(json_string: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Safely parse JSON string.

    Returns:
        Tuple of (success, data, error_message)
    """
    try:
        data = json.loads(json_string)
        return True, data, None
    except json.JSONDecodeError as e:
        return False, None, str(e)

def safe_json_stringify(obj: Any, pretty: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Safely convert object to JSON string.

    Returns:
        Tuple of (success, json_string, error_message)
    """
    try:
        indent = 2 if pretty else None
        json_string = json.dumps(obj, indent=indent, ensure_ascii=False)
        return True, json_string, None
    except (TypeError, ValueError) as e:
        return False, None, str(e)

def truncate_text(text: str, max_length: int = 100, ellipsis: str = "...") -> str:
    """Truncate text to specified length with ellipsis."""
    if not text or not isinstance(text, str):
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(ellipsis)] + ellipsis

def strip_html(html_text: str) -> str:
    """Remove HTML tags from text."""
    if not html_text or not isinstance(html_text, str):
        return ""

    # Remove HTML tags
    clean_text = re.sub(r'<[^>]*>', '', html_text)
    return clean_text.strip()

def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds to human-readable string."""
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return "0s"

    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def parse_time_to_seconds(time_str: Union[str, int, float]) -> float:
    """
    Convert time format to seconds.
    Supports formats: "1:23", "1:23:45", numeric values.
    """
    if isinstance(time_str, (int, float)):
        return max(0, float(time_str))

    if not isinstance(time_str, str):
        return 0.0

    time_str = time_str.strip()

    # Try to parse time format (HH:MM:SS, MM:SS)
    time_match = re.match(r'^(\d{1,2})(?::(\d{1,2}))?(?::(\d{1,2}))?$', time_str)
    if time_match:
        parts = time_match.groups()
        if parts[2] is not None:  # HH:MM:SS
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif parts[1] is not None:  # MM:SS
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds

    # Try to parse as float
    try:
        return max(0, float(time_str))
    except ValueError:
        return 0.0

def format_timestamp(timestamp: Union[int, float, datetime]) -> str:
    """Format timestamp for display."""
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%H:%M:%S")

    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
        if timestamp > 1000000000:  # Unix timestamp
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%H:%M:%S")
        else:  # Duration in seconds
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            return f"{minutes}:{seconds:02d}"

    return str(timestamp)

class PerformanceTimer:
    """Simple performance timer context manager."""

    def __init__(self, label: str, logger: Optional[logging.Logger] = None):
        self.label = label
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.time() - self.start_time) * 1000  # Convert to ms
            self.logger.info(f"{self.label}: {duration:.1f}ms")

def retry_with_backoff(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    logger: Optional[logging.Logger] = None
):
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay on each retry
        logger: Optional logger for retry messages
    """
    log = logger or logging.getLogger(__name__)

    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as error:
            if attempt == max_retries:
                log.error(f"Function failed after {max_retries} attempts: {error}")
                raise error

            delay = initial_delay * (backoff_factor ** (attempt - 1))
            log.warning(f"Attempt {attempt} failed, retrying in {delay:.1f}s: {error}")
            time.sleep(delay)

def validate_json_structure(
    data: Dict[str, Any],
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """
    Validate JSON structure against required and optional fields.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Required field is null: {field}")

    # Check for unexpected fields if optional_fields is provided
    if optional_fields is not None:
        allowed_fields = set(required_fields + optional_fields)
        for field in data.keys():
            if field not in allowed_fields:
                errors.append(f"Unexpected field: {field}")

    return len(errors) == 0, errors

def create_output_filename(
    prefix: str = "output",
    suffix: str = "",
    extension: str = "json",
    timestamp: bool = True
) -> str:
    """Create standardized output filename."""
    parts = [prefix]

    if timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(ts)

    if suffix:
        parts.append(suffix)

    filename = "_".join(parts)
    return f"{filename}.{extension.lstrip('.')}"

def ensure_output_dir(subdir: Optional[str] = None) -> Path:
    """Ensure output directory exists and return path."""
    if subdir:
        output_path = Path(Config.OUTPUT_DIR) / subdir
    else:
        output_path = Path(Config.OUTPUT_DIR)

    output_path.mkdir(parents=True, exist_ok=True)
    return output_path