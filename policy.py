"""Identity & Access controls: per-tool permissions, taint escalation and the human approval gate.

In baseline mode (H_POLICY=0) the policy is evaluated in *shadow*: the call is allowed, but the
decision the policy would have made is recorded as `would_have`. In hardened mode it is enforced.
"""
import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urlparse

import config


@dataclass
class Decision:
    action: str        # what actually happens: allow | ask | deny
    would_have: str    # what the policy says regardless of enforcement
    reason: str
    enforced: bool
    effect: str


class Policy:
    def __init__(self, path=None, enforce: bool | None = None):
        self.path = path or config.POLICY_FILE
        self.enforce = config.H_POLICY if enforce is None else enforce
        with open(self.path, encoding="utf-8") as f:
            self.doc = json.load(f)
        self.tools = self.doc.get("tools", {})
        self.default = self.doc.get("default", {"permission": "deny", "effect": "unknown"})
        self.untrusted = set(self.doc.get("untrusted_sources", []))

    def rule(self, tool: str) -> dict:
        return self.tools.get(tool, self.default)

    def effect(self, tool: str) -> str:
        return self.rule(tool).get("effect", "unknown")

    def is_untrusted_source(self, tool: str) -> bool:
        return tool in self.untrusted

    def decide(self, tool: str, args: dict, tainted: bool = False) -> Decision:
        rule = self.rule(tool)
        action = rule.get("permission", "deny")
        effect = rule.get("effect", "unknown")
        reason = f"rule for {tool}" if tool in self.tools else "no rule for tool -> default"

        domains = rule.get("allow_domains")
        if domains and action != "deny":
            u = urlparse(str(args.get("url", "")))
            host = (u.hostname or "").lower()
            if u.scheme != "mock" and not any(host == d or host.endswith("." + d) for d in domains):
                action, reason = "deny", f"host '{host}' not in allow_domains"

        if (action == "allow" and tainted and self.doc.get("taint_escalation")
                and effect in ("write", "destructive")):
            action, reason = "ask", "state-changing action while untrusted content is in context"

        if self.enforce:
            return Decision(action, action, reason, True, effect)
        return Decision("allow", action, reason + " (policy not enforced)", False, effect)


class Approver:
    """Human approval gate. Modes: ask (terminal prompt), approve (auto-yes), deny (auto-no)."""

    def __init__(self, mode: str | None = None):
        self.mode = mode or config.APPROVAL_MODE

    async def request(self, tool: str, args: dict, reason: str) -> tuple[bool, str]:
        if self.mode == "approve":
            return True, "auto_approve"
        if self.mode == "deny":
            return False, "auto_deny"
        prompt = f"\n[approval needed] {tool} {json.dumps(args, ensure_ascii=False)}\n  reason: {reason}\n  allow? [y/N] "
        answer = await asyncio.to_thread(input, prompt)
        ok = answer.strip().lower() in ("y", "yes")
        return ok, "human_approved" if ok else "human_denied"
