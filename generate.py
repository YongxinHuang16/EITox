import argparse
import json
import os
from pathlib import Path

import pandas as pd
import requests


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "outputs"
MODES = ("1", "2", "3")
MODE_DESCRIPTIONS = {
    "1": "违背社会主义核心价值观",
    "2": "歧视",
    "3": "低级红/高级黑",
}


def build_chat_completions_url(base_url):
    """Accept a service root, /v1 endpoint, or full chat/completions URL."""
    url = base_url.rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return f"{url}/v1/chat/completions"


def safe_path_component(value):
    safe_chars = []
    for char in value:
        if char in '<>:"/\\|?*' or ord(char) < 32:
            safe_chars.append("_")
        else:
            safe_chars.append(char)
    safe_value = "".join(safe_chars).strip(" .")
    return safe_value or "model"


def call_chat_model(messages, api_url, model_name, api_key, timeout, temperature=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            f"API response is not OpenAI Chat Completions compatible: {data}"
        ) from exc


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate model responses for EITox-style prompts."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=MODES,
        help="Evaluation category: 1=违背社会主义核心价值观, 2=歧视, 3=低级红/高级黑.",
    )
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible API URL.")
    parser.add_argument("--model", required=True, help="Model name to evaluate.")
    parser.add_argument(
        "--api-key",
        default=os.getenv("MODEL_API_KEY"),
        help="API key. Can also be set with MODEL_API_KEY.",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="CSV file containing a prompt column.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output root directory. Defaults to outputs/.",
    )
    parser.add_argument("--timeout", type=float, default=120, help="Request timeout.")
    parser.add_argument("--temperature", type=float, help="Optional generation temperature.")
    parser.add_argument("--limit", type=int, help="Only process the first N rows.")
    return parser.parse_args()


def validate_args(args):
    if not args.api_key:
        raise SystemExit("Missing API key: pass --api-key or set MODEL_API_KEY.")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be greater than 0.")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be greater than 0.")


def build_paths(args):
    input_path = Path(args.input_file)
    output_path = (
        Path(args.output_dir)
        / args.mode
        / safe_path_component(args.model)
        / "generations.jsonl"
    )
    return input_path, output_path


def main():
    args = parse_args()
    validate_args(args)

    input_path, output_path = build_paths(args)
    if not input_path.is_file():
        raise SystemExit(f"Dataset not found: {input_path}")

    dataframe = pd.read_csv(input_path)
    if "prompt" not in dataframe.columns:
        raise SystemExit(f"Dataset must contain a prompt column: {input_path}")
    if args.limit is not None:
        dataframe = dataframe.head(args.limit)

    api_url = build_chat_completions_url(args.base_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Mode: {args.mode} ({MODE_DESCRIPTIONS[args.mode]})")
    print(f"Dataset: {input_path}")
    print(f"Model: {args.model}")
    print(f"Output: {output_path}")

    with output_path.open("w", encoding="utf-8") as output_file:
        for position, (index, row) in enumerate(dataframe.iterrows(), start=1):
            print(f"Generating {position}/{len(dataframe)}...")
            prompt = str(row["prompt"])
            record = {
                "index": int(index),
                "mode": args.mode,
                "mode_description": MODE_DESCRIPTIONS[args.mode],
                "prompt": prompt,
                "model": args.model,
                "response": None,
                "error": None,
            }

            try:
                record["response"] = call_chat_model(
                    messages=[{"role": "user", "content": prompt}],
                    api_url=api_url,
                    model_name=args.model,
                    api_key=args.api_key,
                    timeout=args.timeout,
                    temperature=args.temperature,
                )
            except Exception as exc:
                record["error"] = str(exc)
                print(f"Generation failed: {exc}")

            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_file.flush()

    print(f"Done. Generations saved to: {output_path}")


if __name__ == "__main__":
    main()
