from openai import OpenAI


class OpenAICompatProvider:
    """
    Works for OpenAI and any OpenAI-compatible API (Ollama, LM Studio, etc.).

    Ollama:   base_url="http://localhost:11434/v1", api_key="ollama"
    OpenAI:   base_url=None, api_key=<your key>
    LM Studio: base_url="http://localhost:1234/v1", api_key="lm-studio"
    """

    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content.strip()
