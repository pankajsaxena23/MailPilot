import os
import requests
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv(override=True)


# ============================================================
# NVIDIA CONFIGURATION
# ============================================================

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

DEFAULT_MODEL = os.environ.get(
    "NVIDIA_MODEL",
    "meta/llama-3.1-8b-instruct"
).strip()


# Models that can be offered by the application.
# You can change these according to the models available
# in your NVIDIA API account.
FALLBACK_MODELS = [
    DEFAULT_MODEL,
    "meta/llama-3.1-8b-instruct",
]


# Remove duplicates while preserving order
FALLBACK_MODELS = list(dict.fromkeys(FALLBACK_MODELS))


# ============================================================
# GET NVIDIA API KEY
# ============================================================

def get_api_key(api_key=None):
    """
    Get NVIDIA API key.

    Priority:
    1. API key supplied by the request
    2. NVIDIA_API_KEY from environment
    """

    key = (
        api_key
        or os.environ.get("NVIDIA_API_KEY", "")
    ).strip()

    if not key:
        raise ValueError(
            "NVIDIA_API_KEY is not configured. "
            "Add your NVIDIA API key to the .env file."
        )

    return key


# ============================================================
# GET MODEL
# ============================================================

def get_model(model=None):
    """
    Return requested NVIDIA model or configured default model.
    """

    selected_model = (
        model
        or os.environ.get(
            "NVIDIA_MODEL",
            DEFAULT_MODEL
        )
    ).strip()

    if not selected_model:
        selected_model = DEFAULT_MODEL

    return selected_model


# ============================================================
# NVIDIA CHAT REQUEST
# ============================================================

def _nvidia_chat(
    messages,
    api_key=None,
    model=None,
    temperature=0.7,
    max_tokens=1000,
    timeout=60
):
    """
    Send a chat-completion request to NVIDIA API.
    """

    key = get_api_key(api_key)
    selected_model = get_model(model)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        NVIDIA_API_URL,
        headers=headers,
        json=payload,
        timeout=timeout
    )

    # Raise HTTP errors
    response.raise_for_status()

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            "NVIDIA API returned an invalid JSON response."
        )

    # Validate response structure
    choices = result.get("choices")

    if not choices:
        raise RuntimeError(
            "NVIDIA API returned no choices."
        )

    message = choices[0].get("message", {})

    content = message.get("content")

    if content is None:
        raise RuntimeError(
            "NVIDIA API returned an empty response."
        )

    return {
        "content": str(content).strip(),
        "model_used": result.get(
            "model",
            selected_model
        )
    }


# ============================================================
# GENERATE EMAIL
# ============================================================

def generate_email(
    subject,
    tone="Professional",
    additional_instructions="",
    model=None,
    api_key=None
):
    """
    Generate a professional email using NVIDIA AI.
    """

    subject = str(subject or "").strip()
    tone = str(tone or "Professional").strip()
    additional_instructions = str(
        additional_instructions or ""
    ).strip()

    if not subject:
        raise ValueError(
            "Subject or topic is required."
        )

    prompt = f"""
Write a complete professional email based on the following information.

Topic / Subject:
{subject}

Tone:
{tone}
"""

    if additional_instructions:
        prompt += f"""

Additional instructions:
{additional_instructions}
"""

    prompt += """

Requirements:
- Write only the email body.
- Do not include analysis or explanations.
- Do not use placeholder text such as [Name] unless necessary.
- Keep the email natural and human-written.
- Use a clear greeting.
- Make the message concise but useful.
- Use appropriate paragraphs.
- End with a professional closing.
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are MailPilot, an AI email writing "
                "assistant. Generate clear, natural, "
                "professional emails."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    return _nvidia_chat(
        messages=messages,
        api_key=api_key,
        model=model,
        temperature=0.7,
        max_tokens=1000
    )


# ============================================================
# REFINE EMAIL
# ============================================================

def ai_refine_email(
    content,
    instruction,
    tone="Professional",
    model=None,
    api_key=None
):
    """
    Refine an existing email using NVIDIA AI.
    """

    content = str(content or "").strip()
    instruction = str(instruction or "").strip()
    tone = str(tone or "Professional").strip()

    if not content:
        raise ValueError(
            "Email content is required."
        )

    if not instruction:
        raise ValueError(
            "Refinement instruction is required."
        )

    prompt = f"""
Improve the following email according to the user's instruction.

Current Email:
{content}

User Instruction:
{instruction}

Desired Tone:
{tone}

Requirements:
- Preserve the original meaning.
- Improve grammar and readability.
- Make the writing natural and human.
- Do not add unnecessary information.
- Do not explain what you changed.
- Return only the revised email.
"""

    messages = [
        {
            "role": "system",
            "content": (
                "You are MailPilot, an expert email "
                "editing assistant."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    return _nvidia_chat(
        messages=messages,
        api_key=api_key,
        model=model,
        temperature=0.5,
        max_tokens=1200
    )


# ============================================================
# TEST NVIDIA AI CONNECTION
# ============================================================

def test_ai_connection(
    api_key=None,
    model=None
):
    """
    Test whether NVIDIA AI is accessible.
    """

    try:

        result = _nvidia_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a connection testing "
                        "assistant."
                    )
                },
                {
                    "role": "user",
                    "content": "Reply with exactly: OK"
                }
            ],
            api_key=api_key,
            model=model,
            temperature=0,
            max_tokens=10,
            timeout=30
        )

        return {
            "success": True,
            "message": "NVIDIA AI connection successful.",
            "model_used": result.get(
                "model_used",
                get_model(model)
            )
        }

    except requests.exceptions.HTTPError as e:

        response_text = ""

        if e.response is not None:
            try:
                response_text = e.response.text[:500]
            except Exception:
                response_text = ""

        return {
            "success": False,
            "message": (
                "NVIDIA AI request failed."
            ),
            "error": response_text
            or str(e)
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "message": "NVIDIA AI request timed out.",
            "error": "Request timeout."
        }

    except requests.exceptions.ConnectionError:

        return {
            "success": False,
            "message": (
                "Could not connect to NVIDIA AI."
            ),
            "error": "Connection error."
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                "NVIDIA AI connection test failed."
            ),
            "error": str(e)
        }


# ============================================================
# SIMPLE HEALTH CHECK
# ============================================================

def is_ai_configured():
    """
    Return True if an NVIDIA API key is configured.
    """

    key = os.environ.get(
        "NVIDIA_API_KEY",
        ""
    ).strip()

    return bool(
        key
        and key != "your_nvidia_api_key_here"
    )
