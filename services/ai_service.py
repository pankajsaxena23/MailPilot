import os
from google import genai

def generate_email(subject, tone="Professional", additional_instructions=""):
    """
    Generates an email draft using Google Gemini AI with the configured API key and model.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6ILLY636LqsAtqr7jccaN4SErJVyFdyIaLvSXKqb0VqCg")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

    if not api_key:
        raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.")

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"Write a professional email based on the following details:\n"
        prompt += f"Subject/Topic: {subject}\n"
        prompt += f"Tone: {tone}\n"
        if additional_instructions:
            prompt += f"Additional Instructions: {additional_instructions}\n"

        prompt += "\nThe email should have a clear subject line and a body. Do not include placeholder names like [Your Name] if possible, just leave a clean sign-off. Do not include markdown formatting like ```email, just return the raw text."

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise RuntimeError("Gemini API rate limit reached. Please wait a moment and try again.")
        raise RuntimeError(f"Error generating email: {err_str}")
