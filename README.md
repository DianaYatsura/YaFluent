# YaFluentBot - English Tutor Telegram Bot

YaFluent Telegram bot designed to help users learn English using AI-powered tools and Spaced Repetition systems.

## Features

- **Personalized Learning**: Tracks user progress and specific words.
- **AI Integration**: Powered by OpenAI (GPT-4o-mini) for explanations and contextual learning.
- **Pronunciation Assessment**: Uses Azure Speech Services to evaluate and improve speaking skills.
- **Spaced Repetition System (SRS)**: Optimized review schedules based on memory science.
- **Global Dictionary**: Shared database of words and definitions.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Async)
- **Bot Library**: [aiogram v3](https://docs.aiogram.dev/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Background Tasks**: [Celery](https://docs.celeryq.dev/)
- **Quality Tools**: [Ruff](https://beta.ruff.rs/docs/) (Linting & Formatting), Pre-commit hooks
- **Deployment**: [Docker Compose](https://docs.docker.com/compose/)

## Project Structure

```text
YaFluent/
├── bot/                # Telegram bot logic
│   ├── handlers/       # Command and message handlers
│   ├── keyboards/      # Inline and Reply keyboards
│   └── middlewares/    # Custom middlewares (e.g., DB session, user registration)
├── core/               # Configuration (Pydantic Settings) and DB connection
├── migrations/         # Database migrations (Alembic)
├── models/             # SQLAlchemy models
├── services/           # Business logic (OpenAI, Azure, SRS algorithm)
├── tasks/              # Celery worker and periodic tasks
├── main.py             # FastAPI entry point & Webhook configuration
├── docker-compose.yml  # Local development infrastructure
└── pyproject.toml      # Tooling configuration (Ruff)
```

##  Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/DianaYatsura/YaFluentBot.git
cd YaFluentBot
```

### 2. Configure Environment Variables
Create a `core/.env` file (see `core/config.py` for required keys):
```env
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/yafluent
OPENAI_API_KEY=your_key
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=your_region
WEBHOOK_URL=https://your-domain.com/webhook
```

### 3. Run with Docker
```bash
docker-compose up -d
```

### 4. Database Migrations
```bash
alembic upgrade head
```

##  Development

**Ruff** is used for linting and formatting. To run checks manually:
```bash
ruff check . --fix
ruff format .
```

Pre-commit hooks are configured to run automatically on every commit.

## Notice

This source code is provided for viewing and reference purposes only.
