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
        try:
            obj, end = dec.raw_decode(text, i)
            yield obj
            i = end
        except json.JSONDecodeError:
            # Bỏ qua các dòng không phải JSON hợp lệ hoặc dòng trống
            i += 1
            continue


_question_re = re.compile(r"Question:\s*(.+)", re.IGNORECASE)
_code_fence_re = re.compile(r"```(?:sql)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _extract_question(prompt_content: str) -> str:
    if not prompt_content:
        return "N/A"
    m = _question_re.search(prompt_content)
    return m.group(1).strip() if m else prompt_content.strip()


def _clean_sql(text: str) -> str:
    if not text:
        return ""
    m = _code_fence_re.search(text)
    return (m.group(1) if m else text).strip()


def _first(lst, default=""):
    return lst[0] if isinstance(lst, list) and lst else default


def _parse_entry(obj: dict) -> dict:
    # --- SQL Prompt & Question ---
    sql_prompt_block = obj.get("prompt") or {}
    sql_prompt_content = sql_prompt_block.get("prompt", "")
    question = _extract_question(sql_prompt_content)

    # --- Explainer Prompt ---
    # Sửa lỗi: Truy cập vào 'prompt' bên trong 'explain_prompt'
    expl_prompt_block = obj.get("explain_prompt") or {}
    expl_prompt_content = expl_prompt_block.get("prompt", "")

    # LLM draft SQL
    llm_block = obj.get("llm") or {}
    llm_replies = llm_block.get("replies") or []
    llm_text = str(_first(llm_replies)).strip()
    llm_sql = _clean_sql(llm_text)

    # --- SQL LLM Meta ---
    sql_llm_meta_list = llm_block.get("meta") or []
    sql_llm_meta = _first(sql_llm_meta_list, default={})
    sql_usage = sql_llm_meta.get("usage") or {}
    model = sql_llm_meta.get("model", "") # Lấy tên model từ đây

    # --- Explainer LLM Meta ---
    expl_block = obj.get("llm_explainer") or {}
    expl_meta_list = expl_block.get("meta") or []
    expl_meta = _first(expl_meta_list, default={})
    expl_usage = expl_meta.get("usage") or {}

    # Router & Error Router
    router = obj.get("router") or {}
    error_router = obj.get("error_router") or {}
    
    route = "unknown"
    if "no_answer" in router:
        route = "no_answer"
    elif "sql_error" in error_router:
        route = "sql_error"
    elif "sql" in router:
        route = "sql_success"

    # SQL Querier
    sql_q = obj.get("sql_querier") or {}
    query_result = ""
    if route == "sql_error":
        # Lấy thông báo lỗi từ error_router
        query_result = error_router.get("sql_error", "")
    elif route == "sql_success":
        query_result = _first(sql_q.get("results"))
    elif route == "no_answer":
        query_result = router.get("no_answer", "")


    # Explainer
    expl_replies = expl_block.get("replies") or []
    explanation = str(_first(expl_replies)).strip()

    # Lấy token cho từng LLM
    sql_prompt_tokens = sql_usage.get("prompt_tokens", 0)
    sql_completion_tokens = sql_usage.get("completion_tokens", 0)
    expl_prompt_tokens = expl_usage.get("prompt_tokens", 0)
    expl_completion_tokens = expl_usage.get("completion_tokens", 0)

    # Tính tổng
    total_tokens = sql_prompt_tokens + sql_completion_tokens + expl_prompt_tokens + expl_completion_tokens

    return {
        "Question": question,
        "Route": route,
        "SQL_Prompt": sql_prompt_content,
        "LLM_SQL": llm_sql,
        "Query_Result": query_result,
        "Explainer_Prompt": expl_prompt_content,
        "Explanation": explanation,
        "Model": model,
        "SQL_Prompt_Tokens": sql_prompt_tokens if sql_prompt_tokens > 0 else "",
        "SQL_Completion_Tokens": sql_completion_tokens if sql_completion_tokens > 0 else "",
        "Expl_Prompt_Tokens": expl_prompt_tokens if expl_prompt_tokens > 0 else "",
        "Expl_Completion_Tokens": expl_completion_tokens if expl_completion_tokens > 0 else "",
        "Total_Tokens": total_tokens if total_tokens > 0 else "",
    }


def build_dataframe(log_path: Path) -> pd.DataFrame:
    rows = []
    for obj in _iter_json_objects(log_path):
        try:
            rows.append(_parse_entry(obj))
        except Exception:
            # Bỏ qua nếu có lỗi khi phân tích một entry
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
        "SQL_Prompt",
        "LLM_SQL",
        "Query_Result",
        "Explainer_Prompt",
        "Explanation",
        "Model", 
        "SQL_Prompt_Tokens", "SQL_Completion_Tokens",
        "Expl_Prompt_Tokens", "Expl_Completion_Tokens",
        "Total_Tokens",
    ]
    cols = [c for c in cols if c in df.columns]
    #print(df[cols].to_string(index=False))

    out_html = base / "report.html"
    df_html = df.copy()

    # Các cột có thể chứa nội dung dài sẽ được đặt trong thẻ <details>
    long_text_cols = ["SQL_Prompt", "LLM_SQL", "Query_Result", "Explainer_Prompt", "Explanation"]

    for col in long_text_cols:
        if col in df_html.columns:
            # Bỏ qua nếu ô trống để tránh tạo thẻ <details> không cần thiết
            is_not_empty = df_html[col].astype(str).str.strip() != ""
            
            # Bọc nội dung trong thẻ <details> để có thể thu gọn/mở rộng
            # .str.replace('\n', '<br>') để giữ nguyên định dạng xuống dòng khi mở ra
            df_html.loc[is_not_empty, col] = (
                "<details><summary>Click to expand</summary>"
                + df_html.loc[is_not_empty, col].astype(str).str.replace('\n', '<br>', regex=False)
                + "</details>"
            )

    # Chuyển DataFrame thành chuỗi HTML
    html_table = df_html[cols].to_html(index=False, escape=False, border=0, classes="dataframe")

    # Tạo một file HTML hoàn chỉnh với CSS để kiểm soát chiều rộng cột
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>Report</title>
    <style>
        body {{ font-family: sans-serif; }}
        table.dataframe {{
            border-collapse: collapse;
            border: 1px solid #ccc;
        }}
        table.dataframe th, table.dataframe td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
            vertical-align: top; /* Căn lề trên cho các ô */
        }}
        table.dataframe th {{
            background-color: #f2f2f2;
        }}
        /* Đặt chiều rộng tối thiểu cho các cột nội dung dài */
        table.dataframe th:nth-child({cols.index('LLM_SQL') + 1}),
        table.dataframe th:nth-child({cols.index('Query_Result') + 1}),
        table.dataframe th:nth-child({cols.index('Explanation') + 1}) {{
            min-width: 200px;
        }}
        table.dataframe th:nth-child({cols.index('SQL_Prompt') + 1}),
        table.dataframe th:nth-child({cols.index('Explainer_Prompt') + 1}) {{
            min-width: 150px;
        }}
        details > summary {{
            cursor: pointer;
        }}
    </style>
    </head>
    <body>
    <h1>SQL Pipeline Report</h1>
    {html_table}
    </body>
    </html>
    """

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Đã lưu: {out_html}")


if __name__ == "__main__":
    main()