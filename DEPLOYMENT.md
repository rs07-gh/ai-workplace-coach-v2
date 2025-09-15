# Deployment Guide for AI Performance Coaching Framework

This guide covers deploying the AI Performance Coaching Framework on various platforms, with a focus on Streamlit Cloud for easy web hosting.

## Streamlit Cloud Deployment (Recommended)

Streamlit Cloud offers free hosting for Streamlit applications with GitHub integration.

### Prerequisites

1. GitHub repository with your framework code
2. Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
3. OpenAI API key

### Step-by-Step Deployment

1. **Prepare Repository**

```bash
# Ensure all required files are in your repo
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

2. **Configure Secrets**

Create `.streamlit/secrets.toml` (do NOT commit this file):

```toml
[default]
OPENAI_API_KEY = "your_api_key_here"
DEFAULT_MODEL = "gpt-5"
REASONING_EFFORT = "medium"
MAX_TOKENS = 4000
TEMPERATURE = 0.1
```

3. **Deploy on Streamlit Cloud**

- Go to [share.streamlit.io](https://share.streamlit.io)
- Click "New app"
- Connect your GitHub repository
- Set main file to `app.py`
- Add secrets in the Streamlit Cloud dashboard
- Deploy!

### Environment Configuration

For Streamlit Cloud, modify your `src/config.py` to handle Streamlit secrets:

```python
# Add this to config.py for Streamlit Cloud compatibility
import streamlit as st

def get_streamlit_config():
    """Get configuration from Streamlit secrets if available."""
    try:
        if hasattr(st, 'secrets') and st.secrets:
            return {
                'OPENAI_API_KEY': st.secrets.get('OPENAI_API_KEY', ''),
                'DEFAULT_MODEL': st.secrets.get('DEFAULT_MODEL', 'gpt-5'),
                'REASONING_EFFORT': st.secrets.get('REASONING_EFFORT', 'medium'),
                # Add other config values as needed
            }
    except:
        pass
    return {}
```

## Docker Deployment

For containerized deployment on cloud platforms.

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy application code
COPY . .

# Expose port for Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  ai-coach:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEFAULT_MODEL=gpt-5
      - REASONING_EFFORT=medium
    volumes:
      - ./outputs:/app/outputs
      - ./logs:/app/logs
    restart: unless-stopped

  # Optional: Add Redis for session storage
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

### Build and Run

```bash
# Build image
docker build -t ai-coaching-framework .

# Run with environment variables
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/outputs:/app/outputs \
  ai-coaching-framework

# Or use Docker Compose
docker-compose up -d
```

## Cloud Platform Deployment

### Heroku

1. **Prepare Heroku Files**

Create `runtime.txt`:
```
python-3.11.4
```

Create `Procfile`:
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

2. **Deploy to Heroku**

```bash
# Install Heroku CLI and login
heroku create your-app-name

# Set environment variables
heroku config:set OPENAI_API_KEY=your_key_here

# Deploy
git push heroku main
```

### Google Cloud Run

1. **Build and Push Container**

```bash
# Build for Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/ai-coach

# Deploy
gcloud run deploy --image gcr.io/PROJECT_ID/ai-coach --platform managed
```

2. **Set Environment Variables**

```bash
gcloud run services update ai-coach \
  --set-env-vars OPENAI_API_KEY=your_key_here
```

### AWS ECS/Fargate

1. **Create Task Definition**

```json
{
  "family": "ai-coaching-framework",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "ai-coach",
      "image": "your-account.dkr.ecr.region.amazonaws.com/ai-coach:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OPENAI_API_KEY",
          "value": "your_key_here"
        }
      ]
    }
  ]
}
```

## Production Considerations

### Security

1. **API Key Management**
   - Use cloud secret managers (AWS Secrets Manager, Google Secret Manager)
   - Rotate API keys regularly
   - Monitor API usage and set limits

2. **Access Control**
   - Implement authentication (OAuth, SAML)
   - Add IP whitelisting if needed
   - Use HTTPS/TLS encryption

3. **Rate Limiting**
   - Implement request rate limiting
   - Add session-based usage tracking
   - Queue long-running analyses

### Performance

1. **Caching**
   - Cache API responses for similar queries
   - Use Redis for session storage
   - Implement result caching

2. **Scaling**
   - Use horizontal scaling for multiple instances
   - Implement async processing for large datasets
   - Add load balancing

3. **Monitoring**
   - Set up application monitoring (New Relic, DataDog)
   - Monitor API costs and usage
   - Track user engagement and errors

### Example Production Config

```python
# src/production_config.py
import os
from typing import Dict, Any

class ProductionConfig:
    """Production-specific configuration."""

    # Security
    ENABLE_HTTPS_ONLY = True
    SESSION_TIMEOUT_MINUTES = 30
    MAX_CONCURRENT_ANALYSES = 5

    # Performance
    ENABLE_CACHING = True
    CACHE_TTL_SECONDS = 3600
    MAX_UPLOAD_SIZE_MB = 10

    # Monitoring
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    ANALYTICS_TRACKING_ID = os.getenv('ANALYTICS_TRACKING_ID')

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Get Redis configuration for caching."""
        return {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'password': os.getenv('REDIS_PASSWORD'),
            'ssl': os.getenv('REDIS_SSL', 'false').lower() == 'true'
        }
```

## Monitoring and Maintenance

### Health Checks

Add health check endpoint to your Streamlit app:

```python
# Add to app.py
import streamlit as st
from src.coaching_engine import CoachingEngine

def health_check():
    """Simple health check for monitoring."""
    try:
        engine = CoachingEngine()
        test_result = engine.test_configuration()
        return test_result['overall_status']
    except:
        return False

# Add health check route (if using custom server)
@app.route('/health')
def health():
    return {'status': 'healthy' if health_check() else 'unhealthy'}
```

### Logging

Configure structured logging for production:

```python
# src/production_logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        return json.dumps(log_entry)
```

### Backup and Recovery

1. **Data Backup**
   - Regular backup of user sessions and configurations
   - Database backup for user data (if applicable)
   - Export analysis results regularly

2. **Disaster Recovery**
   - Multi-region deployment
   - Automated failover procedures
   - Data replication strategies

## Cost Optimization

### API Cost Management

1. **Token Usage Optimization**
   - Monitor and analyze token consumption
   - Implement prompt optimization
   - Cache similar analyses

2. **Model Selection**
   - Use GPT-4 for complex analyses, GPT-3.5 for simpler tasks
   - Implement dynamic model selection based on complexity

3. **Usage Limits**
   - Set per-user daily/monthly limits
   - Implement subscription tiers
   - Queue non-urgent analyses

## Troubleshooting Deployment Issues

### Common Problems

1. **Memory Issues**
   - Increase container memory allocation
   - Optimize large data processing
   - Implement streaming for large files

2. **Timeout Issues**
   - Increase request timeout settings
   - Implement background processing
   - Add progress indicators

3. **API Rate Limits**
   - Implement exponential backoff
   - Add request queuing
   - Monitor rate limit headers

### Debug Mode

Enable debug mode for troubleshooting:

```python
# Add to your deployment
os.environ['DEBUG_MODE'] = 'true'
os.environ['STREAMLIT_LOGGER_LEVEL'] = 'debug'
```

This comprehensive deployment guide should help you get the AI Performance Coaching Framework running in production on your preferred platform!