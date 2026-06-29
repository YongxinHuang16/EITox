# EITox Evaluation Toolkit

This repository provides a two-stage evaluation toolkit for EITox-style
Chinese safety prompts.

The dataset is not included. Prepare a CSV file with one required column:

```text
prompt
```

## Modes

| Mode | Category |
| --- | --- |
| `1` | 违背社会主义核心价值观 |
| `2` | 歧视 |
| `3` | “低级红”“高级黑” |

## Install

```bash
pip install -r requirements.txt
```

Both scripts use OpenAI-compatible Chat Completions APIs.

## Generate

```bash
python generate.py \
  --mode 1 \
  --input-file path/to/prompts.csv \
  --base-url <MODEL_API_URL> \
  --model <MODEL_NAME> \
  --api-key <MODEL_API_KEY>
```

The model API key can also be set with:

```bash
export MODEL_API_KEY=<MODEL_API_KEY>
```

Default output:

```text
outputs/{mode}/{model}/generations.jsonl
```

## Evaluate

```bash
python evaluate.py \
  --mode 1 \
  --generations-file outputs/1/<MODEL_NAME>/generations.jsonl \
  --judge-base-url <JUDGE_API_URL> \
  --judge-model <JUDGE_MODEL_NAME> \
  --judge-api-key <JUDGE_API_KEY>
```

The judge API key can also be set with:

```bash
export JUDGE_MODEL_API_KEY=<JUDGE_API_KEY>
```

Default output:

```text
outputs/{mode}/{judge_model}/{model}/judgments.jsonl
```

Each judgment contains:

```json
{
  "result": "属于",
  "reason": "一句话解释",
  "score": 7
}
```

