from __future__ import annotations

import asyncio
import logging

import httpx


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiResponseError(RuntimeError):
    pass


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not configured. Set it in the environment before "
                "requesting recommendations."
            )

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.15,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }

        response: httpx.Response | None = None
        last_error: httpx.HTTPError | None = None
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for attempt in range(3):
                try:
                    logging.getLogger("accessible_travel_assistant").info(
                        "gemini_request_started",
                        extra={"gemini_model": self.model, "attempt": attempt + 1},
                    )
                    response = await client.post(url, headers={"x-goog-api-key": self.api_key}, json=body)

                    if response.status_code == 400:
                        # Fallback for API deployments that do not accept systemInstruction or JSON mode.
                        fallback_body = {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                                }
                            ],
                            "generationConfig": {
                                "temperature": 0.15,
                                "maxOutputTokens": 4096,
                            },
                        }
                        response = await client.post(
                            url,
                            params={"key": self.api_key},
                            json=fallback_body,
                        )

                    if response.status_code not in {429, 500, 502, 503, 504}:
                        break
                except httpx.HTTPError as exc:
                    last_error = exc
                    response = None
                    logging.getLogger("accessible_travel_assistant").warning(
                        "gemini_request_retryable_error",
                        extra={"gemini_model": self.model, "attempt": attempt + 1},
                    )

                if attempt < 2:
                    await asyncio.sleep(0.8 * (attempt + 1))

        if response is None:
            raise GeminiResponseError("Gemini API request failed before receiving a response.") from last_error

        if response.status_code >= 400:
            logging.getLogger("accessible_travel_assistant").warning(
                "gemini_request_failed",
                extra={"gemini_model": self.model, "http_status_code": response.status_code},
            )
            raise GeminiResponseError(
                f"Gemini API returned HTTP {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        logging.getLogger("accessible_travel_assistant").info(
            "gemini_request_succeeded",
            extra={"gemini_model": self.model, "http_status_code": response.status_code},
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiResponseError("Gemini response did not include generated text.") from exc
