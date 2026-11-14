#!/usr/bin/env python3
"""Phase 0 bake-off: chạy cùng một bộ câu roleplay qua nhiều model Ollama.

Chỉ dùng thư viện chuẩn. Kết quả ghi vào harness/results/<thời gian>/:
  speed.md    bảng tốc độ và RAM của từng model
  answers.md  câu trả lời đã ẩn tên model (Model A, B, ...) để chấm mù
  key.json    ánh xạ Model A/B/... -> tên model thật (mở sau khi chấm xong)
  raw.json    toàn bộ dữ liệu thô

Ví dụ (từ thư mục gốc dự án, Python của backend):
  backend/.venv/bin/python harness/bakeoff.py --models qwen3.5:9b gemma4:12b sailor2:8b
  backend/.venv/bin/python harness/bakeoff.py --models gemma4:12b --limit 2 --host http://127.0.0.1:11434

run_eval.py (kịch bản `kind: bakeoff`) gọi thẳng `run_bakeoff`.
"""
from __future__ import annotations

import argparse
import json
import random
import string
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HOST = "http://127.0.0.1:11434"
HERE = Path(__file__).resolve().parent

# checks.py nằm cạnh file này; thêm thư mục harness/ vào sys.path để import được cả khi
# bakeoff được import từ nơi khác (ví dụ pytest), không chỉ khi chạy trực tiếp.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# HAN, narration_only giữ ở đây để code cũ `from bakeoff import ...` vẫn chạy.
from checks import HAN, auto_check, narration_only  # noqa: E402,F401


def post(path: str, body: dict, stream: bool = False):
    req = urllib.request.Request(
        HOST + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=600)
    return resp if stream else json.loads(resp.read())


def chat(model: str, messages: list[dict], options: dict, think: bool | None) -> dict:
    """Stream một lượt chat; trả về text, TTFT và số liệu của Ollama."""
    body: dict = {"model": model, "messages": messages, "stream": True, "options": options}
    if think is not None:
        body["think"] = think
    start = time.perf_counter()
    ttft = None
    parts: list[str] = []
    final: dict = {}
    for line in post("/api/chat", body, stream=True):
        if not line.strip():
            continue
        chunk = json.loads(line)
        piece = chunk.get("message", {}).get("content", "")
        if piece:
            if ttft is None:
                ttft = time.perf_counter() - start
            parts.append(piece)
        if chunk.get("done"):
            final = chunk
    eval_s = final.get("eval_duration", 0) / 1e9
    prompt_s = final.get("prompt_eval_duration", 0) / 1e9
    return {
        "text": "".join(parts).strip(),
        "ttft_s": ttft,
        "total_s": time.perf_counter() - start,
        "out_tokens": final.get("eval_count", 0),
        "tok_per_s": final.get("eval_count", 0) / eval_s if eval_s else None,
        "prompt_tokens": final.get("prompt_eval_count", 0),
        "prompt_tok_per_s": final.get("prompt_eval_count", 0) / prompt_s if prompt_s else None,
    }


def chat_safe(model: str, messages: list[dict], options: dict) -> dict:
    """Tắt chế độ thinking nếu model có; thử lại không kèm tham số nếu bị từ chối."""
    try:
        return chat(model, messages, options, think=False)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        return chat(model, messages, options, think=None)


def loaded_size_gb(model: str) -> float | None:
    with urllib.request.urlopen(HOST + "/api/ps", timeout=30) as r:
        for m in json.loads(r.read()).get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return m.get("size", 0) / 1e9
    return None


def unload(model: str) -> None:
    try:
        post("/api/generate", {"model": model, "keep_alive": 0})
    except Exception:
        pass


def avg(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x: float | None, nd: int = 1) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def run_bakeoff(
    models: list[str],
    *,
    prompts: Path = HERE / "prompts.json",
    num_ctx: int = 8192,
    max_tokens: int = 450,
    temperature: float = 0.8,
    seed: int = 7,
    host: str | None = None,
    out_root: Path = HERE / "results",
    limit: int | None = None,
) -> tuple[int, Path | None, list[str]]:
    """Chạy bake-off; trả (mã thoát, thư mục kết quả, các dòng bảng so sánh). `limit`: chỉ chạy N câu đầu
    (run_eval dùng để kiểm nhanh trên model thật). Không in dòng "Đã ghi kết quả vào" (main() in)."""
    global HOST
    if host:
        HOST = host.rstrip("/")
    spec = json.loads(Path(prompts).read_text(encoding="utf-8"))
    cases = spec["cases"][:limit] if limit else spec["cases"]
    options = {
        "num_ctx": num_ctx,
        "num_predict": max_tokens,
        "temperature": temperature,
        "seed": seed,
    }

    try:
        urllib.request.urlopen(HOST + "/api/version", timeout=5)
    except Exception:
        print("Không kết nối được Ollama ở", HOST, "- hãy mở app Ollama trước.", file=sys.stderr)
        return 1, None, []

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(out_root) / stamp
    n = 2
    while out.exists():  # hai lần chạy trong cùng một giây
        out = Path(out_root) / f"{stamp}-{n}"
        n += 1
    out.mkdir(parents=True)
    raw: dict = {"options": options, "models": {}}
    args = argparse.Namespace(models=models, seed=seed)

    for model in args.models:
        print(f"\n=== {model} ===", flush=True)
        try:
            t0 = time.perf_counter()
            chat_safe(model, [{"role": "user", "content": "Xin chào"}], {**options, "num_predict": 8})
            load_s = time.perf_counter() - t0
        except Exception as e:  # model chưa pull, hết RAM, ...
            print(f"  LỖI khi nạp model: {e}")
            raw["models"][model] = {"error": str(e)}
            continue
        size_gb = loaded_size_gb(model)
        runs = []
        for i, case in enumerate(cases, 1):
            system = spec["systems"][case["system"]]
            messages = [{"role": "system", "content": system}, {"role": "user", "content": case["user"]}]
            try:
                r = chat_safe(model, messages, options)
            except Exception as e:
                r = {"text": f"[LỖI: {e}]", "ttft_s": None, "tok_per_s": None, "out_tokens": 0}
            r["case"] = case["id"]
            r["problems"] = auto_check(r["text"], spec.get("checks", {}).get(case["system"], {}))
            runs.append(r)
            note = ", ".join(r["problems"]) or "ok"
            print(f"  [{i}/{len(cases)}] {case['id']}: TTFT {fmt(r['ttft_s'], 2)}s, {fmt(r['tok_per_s'])} tok/s, {note}", flush=True)
        raw["models"][model] = {"load_s": load_s, "size_gb": size_gb, "runs": runs}
        unload(model)

    ok = [m for m in args.models if "runs" in raw["models"].get(m, {})]

    lines = [
        "| Model | RAM nạp (GB) | Nạp lần đầu (s) | TTFT tb (s) | Tốc độ sinh tb (tok/s) | Tốc độ đọc prompt tb (tok/s) | Câu có lỗi máy bắt được |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in ok:
        d = raw["models"][m]
        n_bad = sum(1 for r in d["runs"] if r["problems"])
        lines.append(
            f"| {m} | {fmt(d['size_gb'])} | {fmt(d['load_s'])} | {fmt(avg([r['ttft_s'] for r in d['runs']]), 2)} "
            f"| {fmt(avg([r['tok_per_s'] for r in d['runs']]))} | {fmt(avg([r.get('prompt_tok_per_s') for r in d['runs']]))} "
            f"| {n_bad}/{len(d['runs'])} |"
        )
    for m in args.models:
        if m not in ok:
            lines.append(f"| {m} | lỗi: {raw['models'][m]['error']} | | | | | |")
    problem_lines = ["", "## Lỗi máy bắt được", ""]
    for m in ok:
        for r in raw["models"][m]["runs"]:
            if r["problems"]:
                problem_lines.append(f"- {m} / {r['case']}: {', '.join(r['problems'])}")
    lines += problem_lines
    (out / "speed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rng = random.Random(args.seed)
    labels = list(string.ascii_uppercase[: len(ok)])
    shuffled = ok[:]
    rng.shuffle(shuffled)
    key = dict(zip(labels, shuffled))
    md = [
        "# Chấm mù câu trả lời",
        "",
        "Với mỗi câu, chấm từng model 1-5 theo: tiếng Việt tự nhiên, xưng hô đúng và nhất quán,",
        "không nói/hành động thay người chơi, đúng format (có `[Thought: ...]` ở Story Mode),",
        "không lẫn tiếng Anh/Trung. Chấm xong mới mở key.json.",
        "",
    ]
    for case in cases:
        md += [f"## {case['id']}", "", f"**Người chơi:** {case['user']}", ""]
        for label in labels:
            run = next(r for r in raw["models"][key[label]]["runs"] if r["case"] == case["id"])
            md += [f"### Model {label}", "", run["text"] or "(trống)", "", "Điểm: ", ""]
    (out / "answers.md").write_text("\n".join(md), encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "\n".join(lines))
    return 0, out, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", required=True, help="tag Ollama, ví dụ qwen3.5:9b")
    ap.add_argument("--prompts", default=str(HERE / "prompts.json"))
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--max-tokens", type=int, default=450)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--host", default=HOST, help=f"địa chỉ Ollama (mặc định {HOST})")
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu của prompts.json")
    ap.add_argument("--out-root", default=str(HERE / "results"), help="thư mục chứa kết quả (mặc định harness/results/)")
    args = ap.parse_args(argv)
    code, out, _ = run_bakeoff(
        args.models,
        prompts=Path(args.prompts),
        num_ctx=args.num_ctx,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        seed=args.seed,
        host=args.host,
        out_root=Path(args.out_root),
        limit=args.limit,
    )
    if out is not None:
        print(f"\nĐã ghi kết quả vào {out}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
