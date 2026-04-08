from dotenv import load_dotenv  # type: ignore
import os

def load_env() -> None:
    """
    Load environment variables from the .env file and validate required keys.
    """
    load_dotenv()

    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME",
        "AZURE_OPENAI_API_VERSION",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
