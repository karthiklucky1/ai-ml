from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class GapReasoner:
    """
    Uses OpenAI (new SDK) to detect missing information in prompts
    """

    def reason(self, prompt: str) -> str:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # cheaper + fast (recommended)
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that analyzes a user prompt "
                        "and explains what additional information is missing "
                        "to give a high-quality answer. "
                        "Do NOT assume values. Use natural language."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=150
        )

        return response.choices[0].message.content.strip()
