# V1.0 — Provider streaming + anti-429 (OpenAI / Gemini / Anthropic) + Timeout
from __future__ import annotations
import asyncio
import logging
import random
from typing import Any, AsyncGenerator, Dict, List
import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from .pricing import MODEL_PRICING

logger = logging.getLogger(__name__)

# Timeout global pour les requêtes AI (30 secondes)
AI_REQUEST_TIMEOUT = 30.0


class LLMStreamer:
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        anthropic_client: AsyncAnthropic,
        rate_limits: Dict[str, asyncio.Semaphore],
        *,
        base_delay: float = 2.0,
        max_retries: int = 2,
    ):
        self.openai_client = openai_client
        self.anthropic_client = anthropic_client
        self._rl = rate_limits or {}
        self._rate_base_delay = float(base_delay)
        self._rate_max_retries = int(max_retries)

    async def with_rate_limit_retries(self, provider: str, op_coro_factory: Any) -> Any:
        max_tries = max(1, self._rate_max_retries + 1)
        for attempt in range(max_tries):
            try:
                sem = self._rl.get(provider)
                if sem is not None:
                    async with sem:
                        return await op_coro_factory()
                return await op_coro_factory()
            except Exception as e:
                is_429 = False
                try:
                    from anthropic import RateLimitError as _AnthropicRateLimit

                    if isinstance(e, _AnthropicRateLimit):
                        is_429 = True
                except Exception:
                    pass
                if (
                    getattr(e, "status_code", None) == 429
                    or "429" in str(getattr(e, "status", ""))
                    or "429" in str(e)
                ):
                    is_429 = True
                if not is_429 or attempt == max_tries - 1:
                    raise
                delay = self._rate_base_delay * (2**attempt) + random.random() * 0.5
                logger.warning(
                    f"[rate-limit] {provider} retry in {delay:.1f}s (attempt {attempt + 1}/{max_tries})"
                )
                await asyncio.sleep(delay)

    async def get_llm_response_stream(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        history: List[Dict[str, Any]],
        cost_info_container: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        if provider == "openai":
            streamer = self._get_openai_stream(
                model, system_prompt, history, cost_info_container
            )
        elif provider == "google":
            streamer = self._get_gemini_stream(
                model, system_prompt, history, cost_info_container
            )
        elif provider == "anthropic":
            streamer = self._get_anthropic_stream(
                model, system_prompt, history, cost_info_container
            )
        else:
            raise ValueError(f"Fournisseur LLM non supporté: {provider}")

        # Wrapper avec timeout pour éviter requêtes qui pendent indéfiniment
        try:
            async with asyncio.timeout(AI_REQUEST_TIMEOUT):
                async for chunk in streamer:
                    yield chunk
        except asyncio.TimeoutError:
            logger.error(f"Timeout AI request après {AI_REQUEST_TIMEOUT}s (provider={provider}, model={model})")
            cost_info_container["__error__"] = "timeout"
            yield f"\n\n[Erreur: La requête a expiré après {AI_REQUEST_TIMEOUT}s]"

    async def _get_openai_stream(
        self, model, system_prompt, history, cost_info_container
    ):
        messages = [{"role": "system", "content": system_prompt}] + history
        usage_seen = False
        try:

            async def _op():
                return await self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.4,
                    stream=True,
                    stream_options={"include_usage": True},
                )

            stream = await self.with_rate_limit_retries("openai", _op)
            async for event in stream:
                try:
                    delta = event.choices[0].delta
                    text = getattr(delta, "content", None)
                    if text:
                        yield text
                except Exception:
                    pass
                usage = getattr(event, "usage", None)
                if usage and not usage_seen:
                    usage_seen = True
                    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                    in_tok = getattr(usage, "prompt_tokens", 0)
                    out_tok = getattr(usage, "completion_tokens", 0)
                    total_cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                    cost_info_container.update(
                        {
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_cost": total_cost,
                        }
                    )

                    # Log détaillé pour traçabilité des coûts
                    logger.info(
                        f"[OpenAI] Cost calculated: ${total_cost:.6f} "
                        f"(model={model}, input={in_tok} tokens, output={out_tok} tokens, "
                        f"pricing_input=${pricing['input']:.8f}/token, pricing_output=${pricing['output']:.8f}/token)"
                    )
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}", exc_info=True)
            cost_info_container["__error__"] = "provider_error"

    async def _get_gemini_stream(
        self, model, system_prompt, history, cost_info_container
    ):
        try:

            def _mk_model():
                return genai.GenerativeModel(
                    model_name=model, system_instruction=system_prompt
                )

            async def _op():
                return (_mk_model(),)

            (_model,) = await self.with_rate_limit_retries("google", _op)

            # Convertir l'historique OpenAI/Anthropic vers format Gemini
            # OpenAI: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            # Gemini: Simple string ou list of strings
            gemini_prompt = "\n".join([
                msg.get("content", "") for msg in history if msg.get("content")
            ])

            # COUNT TOKENS INPUT (avant génération)
            input_tokens = 0
            try:
                # Construire prompt complet pour count_tokens (inclut system prompt)
                full_prompt_for_count = system_prompt + "\n" + gemini_prompt

                # Compter tokens input (synchrone mais rapide)
                count_result = _model.count_tokens(full_prompt_for_count)
                input_tokens = count_result.total_tokens
                logger.debug(f"[Gemini] Input tokens: {input_tokens}")
            except Exception as e:
                logger.warning(f"[Gemini] Failed to count input tokens: {e}", exc_info=True)

            # Stream response et accumuler texte
            full_response_text = ""
            resp = await _model.generate_content_async(
                gemini_prompt, stream=True, generation_config={"temperature": 0.4}
            )
            async for chunk in resp:
                try:
                    text = getattr(chunk, "text", None)
                    if not text and getattr(chunk, "candidates", None):
                        cand = chunk.candidates[0]
                        if getattr(cand, "content", None) and getattr(
                            cand.content, "parts", None
                        ):
                            text = "".join(
                                [
                                    getattr(p, "text", "") or str(p)
                                    for p in cand.content.parts
                                    if p
                                ]
                            )
                    if text:
                        full_response_text += text
                        yield text
                except Exception:
                    pass

            # COUNT TOKENS OUTPUT (après génération)
            output_tokens = 0
            try:
                count_result = _model.count_tokens(full_response_text)
                output_tokens = count_result.total_tokens
                logger.debug(f"[Gemini] Output tokens: {output_tokens}")
            except Exception as e:
                logger.warning(f"[Gemini] Failed to count output tokens: {e}", exc_info=True)

            # CALCUL COÛT
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            total_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

            cost_info_container.update({
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_cost": total_cost,
            })

            # Log détaillé pour traçabilité des coûts
            logger.info(
                f"[Gemini] Cost calculated: ${total_cost:.6f} "
                f"(model={model}, input={input_tokens} tokens, output={output_tokens} tokens, "
                f"pricing_input=${pricing['input']:.8f}/token, pricing_output=${pricing['output']:.8f}/token)"
            )
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)
            cost_info_container["__error__"] = "provider_error"

    async def _get_anthropic_stream(
        self, model, system_prompt, history, cost_info_container
    ):
        try:

            async def _op():
                return self.anthropic_client.messages.stream(
                    model=model,
                    max_tokens=1500,
                    temperature=0.4,
                    system=system_prompt,
                    messages=history,
                )

            stream_cm = await self.with_rate_limit_retries("anthropic", _op)
            async with stream_cm as stream:
                async for event in stream:
                    try:
                        if getattr(event, "type", "") == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            if delta:
                                text = getattr(delta, "text", "") or ""
                                if text:
                                    yield text
                    except Exception:
                        pass
                try:
                    final = await stream.get_final_response()
                    usage = getattr(final, "usage", None)
                    if usage:
                        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                        in_tok = getattr(usage, "input_tokens", 0)
                        out_tok = getattr(usage, "output_tokens", 0)
                        total_cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                        cost_info_container.update(
                            {
                                "input_tokens": in_tok,
                                "output_tokens": out_tok,
                                "total_cost": total_cost,
                            }
                        )

                        # Log détaillé pour traçabilité des coûts
                        logger.info(
                            f"[Anthropic] Cost calculated: ${total_cost:.6f} "
                            f"(model={model}, input={in_tok} tokens, output={out_tok} tokens, "
                            f"pricing_input=${pricing['input']:.8f}/token, pricing_output=${pricing['output']:.8f}/token)"
                        )
                    else:
                        logger.warning(f"[Anthropic] No usage data in final response for model {model}")
                except Exception as e:
                    logger.warning(f"[Anthropic] Failed to get usage data: {e}", exc_info=True)
        except Exception as e:
            try:
                from anthropic import RateLimitError as _AnthropicRateLimit

                if isinstance(e, _AnthropicRateLimit) or "429" in str(e):
                    cost_info_container["__error__"] = "rate_limit"
                else:
                    cost_info_container["__error__"] = "provider_error"
            except Exception:
                cost_info_container["__error__"] = "provider_error"
            logger.error(f"Anthropic stream error: {e}", exc_info=True)
