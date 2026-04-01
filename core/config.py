import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "MasterAI Backend")

    # MariaDB / MySQL (XAMPP)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "masterai_db")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")

    # OpenRouter AI
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # OpenAI Direct
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # External APIs
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

    # Adzuna Jobs API (used by jobs/search endpoint)
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "YOUR_FREE_ADZUNA_APP_ID_HERE")
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "YOUR_FREE_ADZUNA_APP_KEY_HERE")

    # Qubrid AI
    QUBRID_API_KEY: str = os.getenv("QUBRID_API_KEY", "")

    # Groq AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEY_FALLBACK: str = os.getenv("GROQ_API_KEY_FALLBACK", "")

    # SMTP (for sending OTP emails)
    # Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USE_TLS=true
    #        Use a Gmail App Password (not your login password)
    # Outlook: SMTP_HOST=smtp.office365.com, SMTP_PORT=587, SMTP_USE_TLS=true
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "")          # your email address
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # App Password for Gmail
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

settings = Settings()
