# visualize.py

import pandas as pd
import re

def parse_log_line(line: str) -> dict:
    """Sử dụng regex để trích xuất thông tin chính từ một dòng log phức tạp."""
    
    # 1. Trích xuất câu hỏi của người dùng
    question_match = re.search(r"Question: (.*?)\\n", line)
    question = question_match.group(1).strip() if question_match else "N/A"
    
    # 2. Xác định luồng xử lý (route) và lấy dữ liệu tương ứng
    if "'router': {'sql':" in line:
        route = "✅ SQL"
        
        # === PHẦN SỬA LỖI BẮT ĐẦU ===
        # Thay đổi regex để lấy SQL từ vị trí đáng tin cậy hơn trong log
        sql_match = re.search(r"'router': {'sql': \['(.*?)'\]}", line, re.DOTALL)
        
        if sql_match:
            # Lấy nội dung và thay thế ký tự xuống dòng `\\n` thành `\n` thật
            sql_query = sql_match.group(1).strip().replace('\\n', '\n')
        else:
            sql_query = "Không tìm thấy SQL."
        # === PHẦN SỬA LỖI KẾT THÚC ===

        # Trích xuất câu trả lời cuối cùng
        final_answer_match = re.search(r"'llm_explainer'.*?text='(.*?)'", line, re.DOTALL)
        final_answer = final_answer_match.group(1).strip().replace('\\n', '<br>') if final_answer_match else "N/A"

    elif "'router': {'no_answer':" in line:
        route = "❌ No Answer"
        sql_query = "N/A"
        
        # Trích xuất lý do không trả lời được
        no_answer_match = re.search(r"'no_answer': '(.*?)'", line)
        final_answer = no_answer_match.group(1).strip() if no_answer_match else "N/A"
        
    else:
        route = "❓ Unknown"
        sql_query = "N/A"
        final_answer = "N/A"
        
    return {
        "Câu hỏi": question,
        "Luồng xử lý": route,
        "SQL được tạo": sql_query,
        "Câu trả lời cuối cùng": final_answer,
    }

def create_visualization(input_file: str = "logs/results.jsonl", output_file: str = "results_visualization.html"):
    """Đọc tệp log, phân tích và tạo một bảng HTML để trực quan hóa."""
    records = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip(): # Bỏ qua các dòng trống
                    records.append(parse_log_line(line))
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp '{input_file}'.")
        return

    if not records:
        print("Không có dữ liệu trong tệp để xử lý.")
        return

    # Tạo DataFrame từ dữ liệu đã trích xuất
    df = pd.DataFrame(records)

    # Định dạng DataFrame thành HTML để đẹp hơn
    html_styler = df.style.set_properties(**{
        'text-align': 'left',
        'white-space': 'pre-wrap', # Cho phép xuống dòng trong ô
        'border': '1px solid #ddd',
        'padding': '10px'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#1E88E5'), 
            ('color', 'white'),
            ('font-weight', 'bold')
        ]},
        {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]},
    ]).hide(axis="index") # Ẩn chỉ số cột của DataFrame

    # Lưu kết quả ra file HTML
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_styler.to_html())
        
    print(f"🚀 Hoàn tất! Mở tệp '{output_file}' trong trình duyệt để xem kết quả.")

if __name__ == "__main__":
    create_visualization()