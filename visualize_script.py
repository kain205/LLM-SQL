import json
import re
from pathlib import Path
import pandas as pd


def _iter_json_objects(filepath: str | Path):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    dec = json.JSONDecoder()
    i, n = 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        obj, end = dec.raw_decode(text, i)
        yield obj
        i = end


_question_re = re.compile(r"Question:\s*(.+)", re.IGNORECASE)


def _extract_question(prompt_content: str) -> str:
    if not prompt_content:
        return "N/A"
    m = _question_re.search(prompt_content)
    return m.group(1).strip() if m else prompt_content.strip()


_code_fence_re = re.compile(r"```(?:sql)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _clean_sql(text: str) -> str:
    if not text:
        return ""
    m = _code_fence_re.search(text)
    return (m.group(1) if m else text).strip()


def _first(lst, default=""):
    return lst[0] if isinstance(lst, list) and lst else default


def _parse_entry(obj: dict) -> dict:
    # Prompt -> Question
    prompt_blocks = (((obj.get("prompt") or {}).get("prompt")) or [])
    prompt_content = prompt_blocks[0].get("content") if prompt_blocks else ""
    question = _extract_question(prompt_content)

    # LLM draft SQL (raw assistant reply)
    llm_replies = ((obj.get("llm") or {}).get("replies")) or []
    llm_text = (llm_replies[0].get("content") or "").strip() if llm_replies else ""
    llm_sql = _clean_sql(llm_text)
    llm_meta = (llm_replies[0].get("meta") or {}) if llm_replies else {}
    usage = llm_meta.get("usage") or {}

    # Router decision
    router = obj.get("router") or {}
    route = "sql" if "sql" in router else ("no_answer" if "no_answer" in router else "unknown")

    # SQL executor
    sql_q = obj.get("sql_querier") or {}
    query_result = _first(sql_q.get("results"))

    # Explainer
    expl = obj.get("llm_explainer") or {}
    expl_replies = expl.get("replies") or []
    explanation = (expl_replies[0].get("content") or "").strip() if expl_replies else ""

    return {
        "Question": question,
        "Route": route,
        "LLM_SQL": llm_sql,
        "Query_Result": query_result,
        "Explanation": explanation,
        "Model": llm_meta.get("model", ""),
        "Prompt_Tokens": usage.get("prompt_tokens", ""),
        "Completion_Tokens": usage.get("completion_tokens", ""),
        "Total_Tokens": usage.get("total_tokens", ""),
    }


def build_dataframe(log_path: Path) -> pd.DataFrame:
    rows = []
    for obj in _iter_json_objects(log_path):
        try:
            rows.append(_parse_entry(obj))
        except Exception:
            # Skip bad records but keep going
            continue
    return pd.DataFrame(rows)


def main():
    base = Path(__file__).parent
    log_file = base / "logs" / "results.jsonl"
    if not log_file.exists():
        print(f"Không tìm thấy file: {log_file}")
        return

    df = build_dataframe(log_file)
    if df.empty:
        print("Không có dữ liệu.")
        return

    # Console view
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 200)
    cols = [
        "Question", "Route",
        "LLM_SQL",
        "Query_Result", "Explanation",
        "Model", "Prompt_Tokens", "Completion_Tokens", "Total_Tokens",
    ]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].to_string(index=False))

    out_html = base / "report.html"
    df[cols].to_html(out_html, index=False, escape=False)
    print(f"Đã lưu: {out_html}")


if __name__ == "__main__":
    main()