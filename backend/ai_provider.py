import os
import requests

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai

load_dotenv()


# =========================================================
# ENVIRONMENT
# =========================================================

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "ollama"
).lower().strip()


# =========================================================
# OLLAMA CONFIG
# =========================================================

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
).rstrip("/")


OLLAMA_URL = (
    f"{OLLAMA_BASE_URL}/api/generate"
)


OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)


# =========================================================
# REQUEST TIMEOUT
# =========================================================

REQUEST_TIMEOUT = int(
    os.getenv(
        "REQUEST_TIMEOUT",
        "300"
    )
)


# =========================================================
# GEMINI CONFIG
# =========================================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = None


if GEMINI_API_KEY:

    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# OLLAMA
# =========================================================

def call_ollama(
    prompt: str,
    temperature: float = 0.2
):

    try:

        print(
            f"AI Provider: Ollama | "
            f"Model: {OLLAMA_MODEL}"
        )

        response = requests.post(

            OLLAMA_URL,

            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },

            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        answer = data.get(
            "response",
            ""
        ).strip()

        if not answer:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Ollama returned "
                    "an empty response."
                )
            )

        return answer


    except requests.Timeout:

        print(
            "Ollama Error: "
            "Request timed out."
        )

        raise HTTPException(
            status_code=504,
            detail=(
                "Local AI took too long "
                "to respond."
            )
        )


    except requests.ConnectionError:

        print(
            "Ollama Error: "
            "Connection failed."
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Local AI service is "
                "not running."
            )
        )


    except requests.RequestException as e:

        print(
            "Ollama Error:",
            e
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Local AI request failed."
            )
        )


# =========================================================
# GEMINI
# =========================================================

def call_gemini(
    prompt: str,
    temperature: float = 0.2,
    json_response: bool = False
):

    if not gemini_client:

        raise HTTPException(
            status_code=503,
            detail=(
                "Production AI is "
                "not configured."
            )
        )


    try:

        print(
            f"AI Provider: Gemini | "
            f"Model: {GEMINI_MODEL}"
        )


        config = {
            "temperature": temperature
        }


        if json_response:

            config[
                "response_mime_type"
            ] = "application/json"


        response = (
            gemini_client
            .models
            .generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config
            )
        )


        answer = getattr(
            response,
            "text",
            None
        )


        if not answer or not answer.strip():

            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an "
                    "empty response."
                )
            )


        return answer.strip()


    except HTTPException:

        raise


    except Exception as e:

        error_text = str(e)

        print(
            "Gemini Error:",
            error_text
        )


        # =================================================
        # 429 / QUOTA
        # =================================================

        if (
            "429" in error_text
            or
            "RESOURCE_EXHAUSTED"
            in error_text
            or
            "quota"
            in error_text.lower()
        ):

            raise HTTPException(
                status_code=429,
                detail=(
                    "AI usage limit has "
                    "been reached. "
                    "Please try again later."
                )
            )


        # =================================================
        # AUTHENTICATION
        # =================================================

        if (
            "401" in error_text
            or
            "403" in error_text
            or
            "API key" in error_text
            or
            "authentication"
            in error_text.lower()
        ):

            raise HTTPException(
                status_code=503,
                detail=(
                    "Production AI "
                    "configuration error."
                )
            )


        # =================================================
        # MODEL NOT FOUND
        # =================================================

        if (
            "404" in error_text
            or
            "NOT_FOUND" in error_text
        ):

            raise HTTPException(
                status_code=503,
                detail=(
                    "Production AI model "
                    "is unavailable."
                )
            )


        # =================================================
        # 503 / TEMPORARY UNAVAILABLE
        # =================================================

        if (
            "503" in error_text
            or
            "UNAVAILABLE" in error_text
        ):

            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini is temporarily "
                    "unavailable. "
                    "Please try again later."
                )
            )


        raise HTTPException(
            status_code=502,
            detail=(
                "Production AI request failed."
            )
        )


# =========================================================
# COMMON PROVIDER
# =========================================================

def generate(
    prompt: str,
    temperature: float = 0.2,
    json_response: bool = False
):

    # =====================================================
    # OLLAMA
    # =====================================================

    if AI_PROVIDER == "ollama":

        return call_ollama(
            prompt=prompt,
            temperature=temperature
        )


    # =====================================================
    # GEMINI
    # =====================================================

    if AI_PROVIDER == "gemini":

        return call_gemini(
            prompt=prompt,
            temperature=temperature,
            json_response=json_response
        )


    # =====================================================
    # INVALID PROVIDER
    # =====================================================

    raise HTTPException(
        status_code=500,
        detail=(
            f"Unsupported AI_PROVIDER: "
            f"{AI_PROVIDER}"
        )
    )