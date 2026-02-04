# Avatar Conversation

A web application for real-time conversations with a custom avatar, powered by **pipecat** pipelines.

## Features

- **Upload Custom Avatar**: Use any image as your avatar
- **Text Chat**: Type messages and get AI responses via Ollama
- **Voice Recording**: Record audio with STT (Groq Whisper)
- **Animated Avatar**: Avatar displays and animates during responses
- **Customizable AI**: Set personality, temperature, and behavior
- **Pipecat Integration**: Uses pipecat services for STT, LLM, TTS

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Web Browser                              │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐   │
│  │ Avatar  │  │  Audio   │  │  Chat   │  │   Settings   │   │
│  │ Canvas  │  │ Record   │  │ History │  │    Panel     │   │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └──────────────┘   │
│       │            │             │                           │
│       └────────────┼─────────────┘                           │
│                    │ WebSocket                               │
└────────────────────┼─────────────────────────────────────────┘
                     │
┌────────────────────┼─────────────────────────────────────────┐
│                    ▼                                          │
│              Flask Server (server.py)                         │
│                    │                                          │
│    ┌───────────────┼───────────────────┐                     │
│    │               │                   │                     │
│    ▼               ▼                   ▼                     │
│ ┌──────┐      ┌─────────┐        ┌─────────┐                │
│ │ STT  │      │   LLM   │        │   TTS   │                │
│ │Groq  │ ──▶  │ Ollama  │  ──▶   │  Groq   │                │
│ │Whisper│      │ Mistral │        │         │                │
│ └──────┘      └─────────┘        └─────────┘                │
│                                                              │
│                  Pipecat Services                            │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Install pipecat with required extras
pip install -e ../../[groq,websocket]

# Or install from pip
pip install pipecat-ai[groq,websocket]

# Install additional requirements
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_MODEL=mistral
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Start Ollama (for LLM)

```bash
ollama serve
ollama pull mistral
```

### 4. Run the Server

```bash
python server.py
```

### 5. Open in Browser

```
http://localhost:5000
```

## Pipecat Services

| Service | Provider | Purpose |
|---------|----------|---------|
| STT | Groq Whisper | Speech-to-Text |
| LLM | Ollama | AI Response Generation |
| TTS | Groq | Text-to-Speech |

## Project Structure

```
avatar_conversation/
├── server.py           # Flask + Pipecat server
├── index.html          # Web interface
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── static/
│   ├── app.js          # Frontend JavaScript
│   └── styles.css      # Styling
├── uploads/            # Uploaded avatar images
└── logs/               # Server logs
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | API key for Groq STT/TTS |
| `OLLAMA_MODEL` | `mistral` | Ollama model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |

### AI Settings (via UI)
- **Avatar Name**: Display name for the assistant
- **Personality**: System prompt defining behavior
- **Temperature**: Response creativity (0-2)
- **Continuous Mode**: Auto-detect speech end

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve web interface |
| `/api/status` | GET | Get server & pipecat status |
| `/api/upload` | POST | Upload avatar image |
| `/api/logs` | GET | Get recent logs |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `connect` | Server→Client | Connection established |
| `send_text` | Client→Server | Send text message |
| `send_audio` | Client→Server | Send audio data |
| `response` | Server→Client | AI response text |
| `avatar_frame` | Server→Client | Avatar video frame |
| `update_settings` | Client→Server | Update AI settings |

## Extending with Full Pipecat Pipeline

To use the full pipecat pipeline architecture with transport:

```python
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.groq.tts import GroqTTSService
from pipecat.transports.websocket.server import WebsocketServerTransport

# Create pipeline
pipeline = Pipeline([
    transport.input(),
    stt_service,
    llm_service,
    tts_service,
    transport.output(),
])

# Run
runner = PipelineRunner()
await runner.run(PipelineTask(pipeline))
```

## Troubleshooting

### Ollama not connected
```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull mistral
```

### Groq API error
- Check your `GROQ_API_KEY` in `.env`
- Get a key from https://console.groq.com

### Port 5000 in use
Edit `server.py`, change the port:
```python
socketio.run(app, host='127.0.0.1', port=5001)
```

## Requirements

- Python 3.8+
- Ollama running locally
- Groq API key (for STT/TTS)
- Modern web browser

## License

BSD 2-Clause License - See LICENSE file in repository root.
