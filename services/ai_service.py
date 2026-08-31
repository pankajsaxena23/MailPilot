import os
import re
from google import genai

FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
]

def get_client(api_key=None):
    """
    Returns an initialized Gemini Client with the given API key or the environment variable.
    """
    key = api_key or os.environ.get("AQ.Ab8RN6ILLY636LqsAtqr7jccaN4SErJVyFdyIaLvSXKqb0VqCg")
    if not key or key == "your_gemini_api_key_here":
        raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.")
    return genai.Client(api_key=key)

def clean_ai_output(text: str) -> str:
    """
    Cleans up any markdown fences, extra whitespace, or AI boilerplate from the response.
    """
    if not text:
        return ""
    
    # Remove markdown code fences like ```email ... ``` or ```markdown ... ``` or ``` ... ```
    text = re.sub(r"^```(?:email|markdown|text|html)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()

def _execute_with_model_fallback(client, prompt: str, preferred_model: str = None) -> tuple[str, str]:
    """
    Executes generate_content with automatic fallback if the preferred model hits
    rate limits, quota limits (429), or model availability issues.
    Returns (generated_text, model_used).
    """
    configured_model = preferred_model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    
    # Build unique candidate models list starting with the preferred model
    models_to_try = [configured_model]
    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return clean_ai_output(response.text), model_name
        except Exception as e:
            err_str = str(e)
            last_error = e
            # If 429, 404, or 503, continue to try the next model in the fallback list
            if any(code in err_str for code in ["429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND", "503", "UNAVAILABLE"]):
                continue
            # For other critical errors, re-raise directly
            raise RuntimeError(f"Error generating email with model {model_name}: {err_str}")

    # If all models failed
    err_str = str(last_error) if last_error else "Unknown error"
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
        raise RuntimeError("Gemini API daily or per-minute quota reached on all available models. Please wait a moment or update your API key.")
    raise RuntimeError(f"Error generating email across all attempted models: {err_str}")

def generate_email(subject: str, tone: str = "Professional", additional_instructions: str = "", model: str = None) -> dict:
    """
    Generates an email draft using Google Gemini AI with the configured API key and model fallback.
    Returns a dictionary with 'content' and 'model_used'.
    """
    client = get_client()

    prompt = (
        f"You are MailPilot, an expert AI email assistant. Write a high-quality, ready-to-send email based on the following requirements:\n\n"
        f"Subject / Topic: {subject}\n"
        f"Tone: {tone}\n"
    )
    if additional_instructions:
        prompt += f"Specific Instructions & Context: {additional_instructions}\n"

    prompt += (
        "\nGuidelines:\n"
        "- The email must be concise, well-structured, polite, and persuasive according to the requested tone.\n"
        "- Do not include placeholders like '[Your Name]', '[Sender Name]', or '[Company Name]' if avoidable; provide natural, complete phrasing or a clean universal sign-off (e.g. 'Best regards,').\n"
        "- Do NOT enclose the email in markdown code blocks (e.g., ```email).\n"
        "- Return only the email body (you may include greeting and sign-off)."
    )

    content, model_used = _execute_with_model_fallback(client, prompt, preferred_model=model)
    return {
        "content": content,
        "model_used": model_used
    }

def ai_refine_email(content: str, instruction: str, tone: str = "Professional", model: str = None) -> dict:
    """
    Refines, rewrites, shortens, expands, or fixes grammar for an existing email draft using Gemini AI.
    """
    client = get_client()

    prompt = (
        f"You are MailPilot, an expert AI email editor. Refine and improve the following email according to the instruction:\n\n"
        f"Instruction: {instruction}\n"
        f"Desired Tone: {tone}\n\n"
        f"--- Original Email ---\n"
        f"{content}\n"
        f"----------------------\n\n"
        f"Requirements:\n"
        f"- Apply the requested changes while maintaining a professional and natural email structure.\n"
        f"- Do NOT wrap the result in code blocks.\n"
        f"- Return only the refined email text."
    )

    refined_content, model_used = _execute_with_model_fallback(client, prompt, preferred_model=model)
    return {
        "content": refined_content,
        "model_used": model_used
    }

def test_ai_connection(api_key: str = None, model: str = None) -> dict:
    """
    Tests the Gemini API connection with a minimal prompt.
    """
    try:
        client = get_client(api_key)
        test_model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        content, model_used = _execute_with_model_fallback(client, "Reply with 'OK' only.", preferred_model=test_model)
        return {
            "success": True,
            "message": f"Connected successfully using {model_used}",
            "model_used": model_used
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
