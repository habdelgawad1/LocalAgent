"""Model backends: an OpenAI-compatible client (Ollama / llama.cpp server) and a scripted stand-in.

The ScriptedLLM replays a fixed list of model responses. Use it to test the logging, the policy and the
judge instantly, without waiting for CPU inference, and to simulate a model that has been manipulated.
"""
import json
import re
import time
import uuid
from dataclasses import dataclass, field

import config

THINK_RE = re.compile(r"<think>.*?</think>", re.S)
TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def new_call_id() -> str:
    return "call_" + uuid.uuid4().hex[:8]


@dataclass
class LLMResult:
    content: str
    tool_calls: list                      # [{"id","name","arguments"(str)}]
    usage: dict = field(default_factory=dict)
    finish_reason: str = ""
    latency_ms: int = 0
    tool_calls_from_text: bool = False    # model wrote the call as text instead of a structured call


def parse_text_tool_calls(content: str) -> list:
    """Some small models emit <tool_call>{...}</tool_call> in the text. Recover those calls."""
    calls = []
    for m in TOOL_CALL_RE.finditer(content or ""):
        try:
            obj = json.loads(m.group(1))
            args = obj.get("arguments", obj.get("parameters", {}))
            calls.append({"id": new_call_id(), "name": obj["name"],
                          "arguments": args if isinstance(args, str) else json.dumps(args)})
        except (json.JSONDecodeError, KeyError):
            continue
    return calls


class OpenAICompatLLM:
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY,
                                  timeout=config.LLM_TIMEOUT, max_retries=0)

    async def chat(self, messages: list, tools: list) -> LLMResult:
        t0 = time.perf_counter()
        resp = await self.client.chat.completions.create(
            model=config.MODEL, messages=messages, tools=tools or None,
            temperature=config.TEMPERATURE, max_tokens=config.MAX_TOKENS)
        choice = resp.choices[0]
        content = THINK_RE.sub("", choice.message.content or "").strip()
        calls = [{"id": tc.id or new_call_id(), "name": tc.function.name,
                  "arguments": tc.function.arguments or "{}"} for tc in (choice.message.tool_calls or [])]
        from_text = False
        if not calls:
            calls = parse_text_tool_calls(content)
            if calls:
                from_text = True
                content = TOOL_CALL_RE.sub("", content).strip()
        usage = {}
        if resp.usage:
            usage = {"prompt_tokens": resp.usage.prompt_tokens,
                     "completion_tokens": resp.usage.completion_tokens}
        return LLMResult(content, calls, usage, choice.finish_reason or "",
                         round((time.perf_counter() - t0) * 1000), from_text)


class ScriptedLLM:
    """Replays [{"content": str, "tool_calls": [{"name": str, "arguments": {...}}]}, ...] in order."""

    def __init__(self, script: list):
        self.script = list(script)
        self.i = 0

    async def chat(self, messages: list, tools: list) -> LLMResult:
        if self.i >= len(self.script):
            return LLMResult("(script exhausted)", [], {}, "stop", 0)
        item = self.script[self.i]
        self.i += 1
        calls = []
        for tc in item.get("tool_calls", []):
            raw = tc["arguments_raw"] if "arguments_raw" in tc else json.dumps(tc.get("arguments", {}))
            calls.append({"id": new_call_id(), "name": tc["name"], "arguments": raw})
        return LLMResult(item.get("content", ""), calls, {"scripted": True}, "tool_calls" if calls else "stop", 0)
