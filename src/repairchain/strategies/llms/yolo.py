__all__ = ("yolo",)

import openai


def yolo(prompt: str, model: str = "oai-gpt-4o") -> None:
    # NOTE fix the base_url to use the address for litellm for competition
    client = openai.OpenAI(api_key="anything", base_url="http://0.0.0.0:4000")

    messages = [
        {"role": "system", "content": "You are an expert security analyst."},
        {"role": "system", "content": "You can find security vulnerabilities and suggest patches to fix them."},
        {"role": "system", "content": "You always do minimal changes to the code."},
        {"role": "user", "content": prompt},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    print(response.choices[0].message.content)
    print(response)
