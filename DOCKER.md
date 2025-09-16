# 🐳 Docker Setup

## Quick Start

Run the entire application with a single command:

```bash
./docker-run.sh
```

Or manually with Docker Compose:

```bash
docker-compose up --build
```

## Manual Setup

1. **Ensure .env file exists with your API keys**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Build and run**:
   ```bash
   docker-compose up --build -d
   ```

3. **Access the application**:
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs

## Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up --build

# Remove everything (including volumes)
docker-compose down -v --remove-orphans
```

## Architecture

- **Backend**: FastAPI + Python 3.12 + UV (Port 8000)
- **Frontend**: Next.js + React (Port 3000)
- **Network**: Bridge network for service communication
- **Health Checks**: Both services have health monitoring

## Environment Variables

Required in `.env` file:
- `OPENAI_API_KEY`: Your OpenAI API key
- `LANGSMITH_API_KEY`: (Optional) LangSmith tracing
- `LANGCHAIN_PROJECT`: LangSmith project name

## Troubleshooting

1. **Port conflicts**: Make sure ports 3000 and 8000 are free
2. **Missing .env**: Copy from .env.example and add your keys
3. **Docker not running**: Start Docker Desktop
4. **Build issues**: Run `docker-compose down` then `docker-compose up --build`