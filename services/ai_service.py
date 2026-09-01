import os
import requests

# We define fallback models for the UI drop-down.
FALLBACK_MODELS = [
    "meta/llama-3.1-70b-instruct",
    "google/gemma-2-27b-it",
    "google/diffusiongemma-26b-a4b-it"
]

def get_nvidia_headers(api_key: str = None):
    """
    Returns headers for Nvidia API. Uses the provided key, environment variable, 
    or the hardcoded working key you provided.
    """
    key = (api_key or os.environ.get("NVIDIA_API_KEY", "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")).strip()
    return {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }

def clean_ai_output(text: str) -> str:
    """
    Cleans up markdown code fences from the response.
    """
    if not text:
        return ""
    
    text = text.strip()
    for prefix in ["```email", "```markdown", "```text", "```html", "```"]:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].lstrip()
            break
            
    if text.endswith("```"):
        text = text[:-3].rstrip()
        
    return text

def _execute_nvidia_api(prompt: str, preferred_model: str = None, api_key: str = None) -> tuple[str, str]:
    """
    Executes the prompt against the NVIDIA API.
    """
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = get_nvidia_headers(api_key)
    
    # Use the model requested by the user
    model_name = preferred_model or "google/diffusiongemma-26b-a4b-it"
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": model_name,
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.95
    }
    
    response = requests.post(invoke_url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return clean_ai_output(content), model_name
    else:
        err_msg = response.text
        raise RuntimeError(f"NVIDIA API Error {response.status_code}: {err_msg}")


def generate_email(subject: str, tone: str = "Professional", additional_instructions: str = "", model: str = None, api_key: str = None) -> dict:
    """
    Generates a high-quality email draft using the NVIDIA API.
    """
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
        "- Do not include placeholders like '[Your Name]'; provide natural, complete phrasing or a clean universal sign-off (e.g. 'Best regards,').\n"
        "- Do NOT enclose the email in markdown code blocks (e.g., ```email).\n"
        "- Return only the email body (including greeting and sign-off)."
    )

    content, model_used = _execute_nvidia_api(prompt, preferred_model=model, api_key=api_key)
    return {
        "content": content,
        "model_used": model_used
    }

def ai_refine_email(content: str, instruction: str, tone: str = "Professional", model: str = None, api_key: str = None) -> dict:
    """
    Refines an existing email draft using the NVIDIA API.
    """
    prompt = (
        f"You are MailPilot, an expert AI email editor. Refine and improve the following email according to the instruction:\n\n"
        f"Instruction: {instruction}\n"
        f"Desired Tone: {tone}\n\n"
        f"--- Original Email ---\n"
        f"{content}\n"
        f"----------------------\n\n"
        f"Requirements:\n"
        f"- Apply the requested changes while maintaining a professional and natural email structure.\n"
        "- Do NOT wrap the result in code blocks.\n"
        "- Return only the refined email text."
    )

    refined_content, model_used = _execute_nvidia_api(prompt, preferred_model=model, api_key=api_key)
    return {
        "content": refined_content,
        "model_used": model_used
    }

def test_ai_connection(api_key: str = None, model: str = None) -> dict:
    """
    Tests the NVIDIA API connection with a minimal prompt.
    """
    try:
        content, model_used = _execute_nvidia_api("Reply with 'OK' only.", preferred_model=model, api_key=api_key)
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
