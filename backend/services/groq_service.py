import json
import logging

logger = logging.getLogger(__name__)


class GroqService:
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-20b", demo_mode: bool = False):
        self.api_key = api_key
        self.model = model
        self.demo_mode = demo_mode or not api_key
        self.client = None
        self.fallback_invocations: int = 0  # §7: incremented every time _demo_response is used
        if not self.demo_mode:
            try:
                from groq import Groq

                self.client = Groq(api_key=api_key)
            except Exception as exc:
                logger.error("Failed to init Groq client: %s", exc)
                self.demo_mode = True

    @property
    def is_live(self) -> bool:
        """True only when a real Groq client is configured and not in demo mode."""
        return not self.demo_mode and self.client is not None

    def chat(self, messages: list, system_prompt: str | None = None, max_tokens: int = 1500) -> str:
        if self.demo_mode:
            self.fallback_invocations += 1
            return self._demo_response(messages, system_prompt)
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("Groq API error: %s", exc)
            self.fallback_invocations += 1
            return self._demo_response(messages, system_prompt)

    def extract_json(self, prompt: str, system_prompt: str | None = None, max_tokens: int = 800) -> str:
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )

    def _demo_response(self, messages: list, system_prompt: str | None) -> str:  # noqa: C901
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break

        if system_prompt and "extract" in system_prompt.lower():
            if "decision" in user_msg or "document" in user_msg:
                return json.dumps(
                    {
                        "decisions": [
                            {
                                "title": "Use event-driven architecture",
                                "reasoning": "Decouples services and improves scalability for async workflows.",
                                "related_components": ["ApiGateway"],
                            }
                        ]
                    }
                )
            return json.dumps({"entities": ["AuthModule", "JWT"]})

        if "jwt" in user_msg or "auth" in user_msg:
            return (
                "Based on the **JWT over sessions** decision (AuthModule): the team chose JWT because "
                "the client needs a mobile app with offline-capable auth tokens. Stateless tokens also "
                "simplify horizontal scaling.\n\n"
                "**Sources:** Decision — JWT over sessions; Component — AuthModule"
            )
        if "postgres" in user_msg or "database" in user_msg or "mongo" in user_msg:
            return (
                "Based on the **PostgreSQL over MongoDB** decision (DatabaseLayer): relational data with "
                "strict ACID requirements for billing and user accounts drove this choice. PostgreSQL "
                "provides mature tooling plus JSON columns where flexibility is needed.\n\n"
                "**Sources:** Decision — PostgreSQL over MongoDB; Component — DatabaseLayer"
            )
        return (
            "I'm Halite, your project knowledge assistant. Based on the available graph context, "
            "I can help explain architectural decisions and how they relate to components. "
            "Try asking about JWT, authentication, or database choices."
        )
