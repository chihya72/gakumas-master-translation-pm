import argparse
import json
import os
import time
import re
from pathlib import Path
from typing import Dict, Any, List

from openai import OpenAI
from tqdm import tqdm


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Any):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def chunked(items: List[Dict[str, str]], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def read_checkpoint(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    results = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            results[item["key"]] = item
    return results


def append_checkpoint(path: Path, items: List[Dict[str, Any]]):
    with path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])

    raise ValueError("模型返回不是合法 JSON")


def build_prompt(batch: List[Dict[str, str]]) -> str:
    return f"""
你是专业的日中游戏本地化审校员。

你的任务：判断每条 japanese 和 chinese 是否“语义不匹配”。

重点：
- 不是检查是否逐字翻译。
- 不是检查是否有同样的词。
- 不是检查风格是否自然。
- 只判断中文是否表达了日文的核心意思。

判定为 mismatch=true 的情况：
1. 中文和日文表达的意思完全不同。
2. 中文把日文翻成了另一个功能、按钮、标题、说明。
3. 中文遗漏了核心动作、对象、条件、数量。
4. 中文方向相反，例如 开启/关闭、增加/减少、进入/退出。
5. 中文是无关占位内容，导致无法表达日文意思。

判定为 mismatch=false 的情况：
1. 中文是意译，但意思一致。
2. 中文语序不同，但意思一致。
3. 中文略微简化，但核心意思没变。
4. 游戏术语翻译不够自然，但还能表达同一个意思。
5. 换行、标点、空格不同。

请只输出 JSON，不要输出解释文字。

输出格式：
{{
  "results": [
    {{
      "key": "字段名",
      "mismatch": true,
      "confidence": 0.95,
      "reason": "简短说明为什么不匹配",
      "suggested_chinese": "如果能确定，给出建议译文；不确定则为空字符串"
    }}
  ]
}}

注意：
- 每个输入 key 都必须返回一条结果。
- confidence 表示你对 mismatch 判断的置信度。
- 如果 mismatch=false，reason 可以简短写“语义一致”。

待检查数据：
{json.dumps(batch, ensure_ascii=False, indent=2)}
""".strip()


def call_model(client: OpenAI, model: str, batch: List[Dict[str, str]], retries: int = 3):
    prompt = build_prompt(batch)
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是严谨的日中翻译语义审校工具。你只输出合法 JSON。",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0,
            )

            content = resp.choices[0].message.content or ""
            data = extract_json(content)
            results = data.get("results", [])

            source_map = {x["key"]: x for x in batch}
            final_results = []

            for r in results:
                key = r.get("key")
                if key not in source_map:
                    continue

                src = source_map[key]

                final_results.append({
                    "key": key,
                    "japanese": src["japanese"],
                    "chinese": src["chinese"],
                    "mismatch": bool(r.get("mismatch", False)),
                    "confidence": float(r.get("confidence", 0)),
                    "reason": str(r.get("reason", "")),
                    "suggested_chinese": str(r.get("suggested_chinese", "")),
                })

            returned_keys = {x["key"] for x in final_results}

            for item in batch:
                if item["key"] not in returned_keys:
                    final_results.append({
                        "key": item["key"],
                        "japanese": item["japanese"],
                        "chinese": item["chinese"],
                        "mismatch": False,
                        "confidence": 0,
                        "reason": "模型未返回该字段，未判定。",
                        "suggested_chinese": "",
                    })

            return final_results

        except Exception as e:
            last_error = e
            print(f"[WARN] 第 {attempt} 次调用失败：{e}")
            time.sleep(attempt * 2)

    raise RuntimeError(f"模型调用失败：{last_error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="输入 JSON 文件")
    parser.add_argument("-o", "--output", default="semantic_mismatch_report.json")
    parser.add_argument("--checkpoint", default="semantic_mismatch_checkpoint.jsonl")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--confidence", type=float, default=0.75, help="只输出高于该置信度的 mismatch")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("MODEL", "deepseek-v4-pro")

    if not api_key:
        raise RuntimeError("请设置 OPENAI_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    input_path = Path(args.input)
    output_path = Path(args.output)
    checkpoint_path = Path(args.checkpoint)

    data = load_json(input_path)

    if not isinstance(data, dict):
        raise ValueError("输入 JSON 顶层必须是对象")

    done = read_checkpoint(checkpoint_path)

    pending = []

    for key, value in data.items():
        if key in done:
            continue

        if not isinstance(value, dict):
            continue

        japanese = value.get("japanese", "")
        chinese = value.get("chinese", "")

        if not isinstance(japanese, str) or not isinstance(chinese, str):
            continue

        pending.append({
            "key": key,
            "japanese": japanese,
            "chinese": chinese,
        })

    batches = list(chunked(pending, args.batch_size))

    for batch in tqdm(batches, desc="Checking semantic mismatch"):
        results = call_model(client, model, batch)
        append_checkpoint(checkpoint_path, results)
        for r in results:
            done[r["key"]] = r

    mismatches = [
        x for x in done.values()
        if x.get("mismatch") is True
        and float(x.get("confidence", 0)) >= args.confidence
    ]

    mismatches.sort(
        key=lambda x: (
            -float(x.get("confidence", 0)),
            x.get("key", "")
        )
    )

    report = {
        "input": str(input_path),
        "model": model,
        "checked_count": len(done),
        "mismatch_count": len(mismatches),
        "confidence_threshold": args.confidence,
        "mismatches": mismatches,
    }

    save_json(output_path, report)

    print(f"检查完成：{len(done)} 条")
    print(f"语义不匹配：{len(mismatches)} 条")
    print(f"输出文件：{output_path}")
    print(f"断点文件：{checkpoint_path}")


if __name__ == "__main__":
    main()