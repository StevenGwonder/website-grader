#!/usr/bin/env python3
"""
Devstral Coding Worker - spawned by Sierra via delegate_task.

Receives a coding task, calls devstral-2:123b via Ollama Cloud,
writes code to disk, runs tests, returns compact summary.

Usage:
    python3 devstral_worker.py --task-file /tmp/task.json
"""
import argparse
import json
import os
import re
import subprocess
import time
import requests

OLLAMA_BASE = "https://ollama.com/v1"
MODEL = "devstral-small-2:24b"
FALLBACK_MODEL = "devstral-small-2:24b"  # Same model — Sierra takes over on failure, no model switch
MAX_TOKENS = 4000
TEMPERATURE = 0.3
TIMEOUT = 180

PONYTAIL_SYSTEM = """You are a Python coding assistant following the PONYTAIL principle:
- Simplest thing that actually works
- No over-engineering, no speculative abstraction
- No factories with one product, no interfaces with one implementation
- No wrappers that only delegate, no config nobody sets
- Use stdlib when possible, prefer native solutions
- Delete dead code, unused imports, default args that match defaults
- Same logic in fewer lines = better

Write CLEAN, MINIMAL Python code. No explanations unless asked.
Output code in triple-backtick python blocks. One file per block, with the filename as a comment on the first line.
"""

def load_api_key():
    """Load OLLAMA API key from ~/.hermes/.env"""
    env_path = os.path.expanduser("~/.hermes/.env")
    prefix = "OLLAMA" + "_API" + "_KEY" + "="
    with open(env_path) as f:
        for line in f:
            if line.startswith(prefix):
                return line.split("=", 1)[1].strip()
    return None

def call_devstral(messages, model=MODEL, max_tokens=MAX_TOKENS):
    """Call Devstral via Ollama Cloud. Returns (content, tokens_used, elapsed)."""
    api_key = load_api_key()
    if not api_key:
        raise RuntimeError("No OLLAMA API key found in ~/.hermes/.env")

    start = time.time()
    resp = requests.post(
        f"{OLLAMA_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": TEMPERATURE,
        },
        timeout=TIMEOUT,
    )
    elapsed = time.time() - start

    if resp.status_code != 200:
        if model != FALLBACK_MODEL:
            return call_devstral(messages, model=FALLBACK_MODEL, max_tokens=max_tokens)
        raise RuntimeError(f"Devstral API error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens = usage.get("total_tokens", 0)
    return content, tokens, elapsed

def extract_code_blocks(text):
    """Extract python code blocks from LLM response. Returns {filename: code}."""
    blocks = {}
    pattern = r"```python\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    for block in matches:
        lines = block.strip().split("\n")
        first_line = lines[0].strip()
        if first_line.startswith("#") and ("." in first_line):
            filename = first_line.lstrip("# ").strip()
            code = "\n".join(lines[1:]).strip()
        else:
            filename = "output.py"
            code = block.strip()
        blocks[filename] = code
    return blocks

def read_file_safe(path):
    try:
        with open(path) as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return ""

def run_command(cmd, cwd=None, timeout=60):
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def process_task(task_file):
    with open(task_file) as f:
        task = json.load(f)

    project_dir = task["project_dir"]
    objective = task["objective"]
    plan_section = task.get("plan_section", "")
    files_to_read = task.get("files_to_read", [])
    files_to_create = task.get("files_to_create", [])
    test_command = task.get("test_command", "")
    task_id = task.get("task_id", "unknown")

    # 1. Build context
    file_context = ""
    for rel_path in files_to_read:
        abs_path = os.path.join(project_dir, rel_path)
        content = read_file_safe(abs_path)
        if content:
            file_context += f"\n--- FILE: {rel_path} ---\n{content}\n"

    # 2. Build prompt
    user_prompt = f"""TASK: {objective}

PROJECT DIR: {project_dir}

FILES TO CREATE: {json.dumps(files_to_create)}

PLAN (follow this exactly):
{plan_section}

EXISTING CODE CONTEXT:
{file_context}

INSTRUCTIONS:
1. Create each file listed in FILES TO_CREATE
2. Follow the plan exactly
3. Use existing code patterns from context files
4. First line of each code block: comment with filename (e.g., # checks/technical.py)
5. Ponytail: simplest thing that works, no over-engineering
6. Write complete file contents, not stubs

Output each file in a separate python code block."""

    messages = [
        {"role": "system", "content": PONYTAIL_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    # 3. Call Devstral
    print(f"[devstral] Calling {MODEL} for task: {task_id}")
    try:
        content, tokens, elapsed = call_devstral(messages)
    except Exception as e:
        return {"task_id": task_id, "status": "error", "error": f"LLM call failed: {e}"}

    print(f"[devstral] Response: {tokens} tokens, {elapsed:.1f}s")

    # 4. Extract and write code
    blocks = extract_code_blocks(content)
    if not blocks:
        return {"task_id": task_id, "status": "error", "error": "No code blocks found", "raw_response": content[:2000]}

    written_files = []
    for filename, code in blocks.items():
        abs_path = os.path.join(project_dir, filename)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as f:
            f.write(code + "\n")
        written_files.append(filename)
        print(f"[devstral] Wrote {filename} ({len(code)} chars)")

    # 5. Run tests
    test_output = ""
    test_exit = None
    if test_command:
        print(f"[devstral] Running tests: {test_command}")
        test_exit, test_stdout, test_stderr = run_command(test_command, cwd=project_dir, timeout=120)
        test_output = (test_stdout + test_stderr).strip()
        if len(test_output) > 3000:
            test_output = test_output[:1500] + "\n...[truncated]...\n" + test_output[-1500:]
        print(f"[devstral] Test exit code: {test_exit}")

    # 6. Return compact summary
    return {
        "task_id": task_id,
        "status": "pass" if test_exit == 0 else ("written" if not test_command else "fail"),
        "model": MODEL,
        "tokens_used": tokens,
        "elapsed_s": round(elapsed, 1),
        "files_written": written_files,
        "test_exit_code": test_exit,
        "test_output": test_output[-2000:] if test_output else "",
    }

def main():
    parser = argparse.ArgumentParser(description="Devstral Coding Worker")
    parser.add_argument("--task-file", required=True, help="Path to task JSON file")
    args = parser.parse_args()
    result = process_task(args.task_file)
    print("\n" + "=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)

if __name__ == "__main__":
    main()
