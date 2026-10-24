"""Entry point.

Interactive:      python main.py
One-shot turns:   python main.py --prompt "list my notes" --prompt "/new" --prompt "what did I ask before?"
Scripted model:   python main.py --script scenarios/injection_demo.json --prompt "Summarise mock://injection_test"

'/new' starts a fresh session (empty context, memory kept). '/quit' ends the run.
"""
import argparse
import asyncio
import json
import re
from datetime import datetime

import config
import seed
from agent import Agent
from envwatch import EnvWatcher
from llm import OpenAICompatLLM, ScriptedLLM
from logger import TraceLogger
from mcp_hub import MCPHub
from memory import MemoryStore
from policy import Approver, Policy


async def amain(args):
    seed.ensure()
    name = re.sub(r"[^\w.-]+", "_", args.name or ("hardened" if config.HARDENED else "baseline"))
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + name
    run_dir = config.LOGS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"RUN_DIR={run_dir}", flush=True)

    log = TraceLogger(run_dir, run_id, echo=args.echo)
    watcher = EnvWatcher({"sandbox": config.SANDBOX_DIR, "outside": config.OUTSIDE_DIR},
                         config.TICKETS_DB, config.MEMORY_DB)
    memory = MemoryStore()
    policy = Policy()
    approver = Approver()
    if args.script:
        with open(args.script, encoding="utf-8") as f:
            llm = ScriptedLLM(json.load(f))
    else:
        llm = OpenAICompatLLM()

    async with MCPHub(config.SERVERS, config.server_env(run_dir), run_dir, log) as hub:
        agent = Agent(llm, hub, memory, policy, approver, watcher, log)
        agent.start_session()

        async def handle(text: str) -> bool:
            """Returns False to stop the run."""
            nonlocal agent
            if text in ("/quit", "/exit"):
                return False
            if text == "/new":
                agent.end_session()
                agent.start_session()
                print("[new session started; long-term memory kept]")
                return True
            answer = await agent.run_turn(text)
            print(f"\nassistant> {answer}\n", flush=True)
            return True

        if args.prompt:
            for p in args.prompt:
                print(f"you> {p}")
                if not await handle(p):
                    break
        else:
            print("Type a message. /new = new session, /quit = exit.")
            while True:
                try:
                    text = (await asyncio.to_thread(input, "you> ")).strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if text and not await handle(text):
                    break
        agent.end_session()
    log.close()
    print(f"Trace written to {run_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", action="append", help="user message (repeatable; '/new' starts a new session)")
    ap.add_argument("--script", help="JSON file of scripted model responses (no real model needed)")
    ap.add_argument("--name", help="label for this run's log folder")
    ap.add_argument("--echo", action="store_true", help="print trace events live")
    asyncio.run(amain(ap.parse_args()))


if __name__ == "__main__":
    main()
