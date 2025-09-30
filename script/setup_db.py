import os
import sqlalchemy
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL in .env")

engine = create_engine(DATABASE_URL, future=True)

def setup_database():
    """
    Drops existing tables and recreates them with fresh sample data.
    This is useful for development to reset the database to a known state.
    """
    print("Resetting database...")
    with engine.begin() as conn:
        # --- PHẦN 1: DROP TẤT CẢ CÁC BẢNG ---
        # Drop các bảng theo thứ tự ngược lại của sự phụ thuộc (bảng con trước, bảng cha sau)
        # Hoặc đơn giản là dùng CASCADE
        print("Dropping tables 'violations', 'chat_messages', 'chat_sessions' if they exist...")
        conn.execute(text("DROP TABLE IF EXISTS public.violations CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS public.chat_messages CASCADE;")) # Thêm vào
        conn.execute(text("DROP TABLE IF EXISTS public.chat_sessions CASCADE;"))  # Thêm vào

        # --- PHẦN 2: TẠO LẠI CÁC BẢNG ---
        # Tạo bảng violations
        print("Creating 'violations' table...")
        conn.execute(text("""
            CREATE TABLE public.violations (
                id SERIAL PRIMARY KEY,
                employee_name TEXT,
                department TEXT,
                violation_type TEXT,
                area TEXT,
                violation_time TIMESTAMP,
                status TEXT
            );
        """))

        # Tạo bảng chat_sessions (phải tạo trước chat_messages vì có foreign key)
        print("Creating 'chat_sessions' table...")
        conn.execute(text("""
            CREATE TABLE public.chat_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            );
        """))
        
        # Tạo bảng chat_messages
        print("Creating 'chat_messages' table...")
        conn.execute(text("""
            CREATE TABLE public.chat_messages (
                id BIGSERIAL PRIMARY KEY,
                session_id UUID NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );
        """))

        # --- PHẦN 3: THÊM DỮ LIỆU MẪU (NẾU CẦN) ---
        print("Inserting sample data for 'violations'...")
        conn.execute(text("""
            INSERT INTO public.violations (employee_name, department, violation_type, area, violation_time, status) VALUES
            -- ... (dữ liệu mẫu của bạn giữ nguyên) ...
            ('Nguyen Van A', 'Production', 'Arriving late', 'Workshop Floor', NOW() - INTERVAL '15 days', 'Resolved'),
            ('Nguyen Van A', 'Production', 'Missing safety gear', 'Workshop Floor', NOW() - INTERVAL '10 days', 'Resolved'),
            ('Nguyen Van A', 'Production', 'Improper conduct', 'Office Zone', NOW() - INTERVAL '2 days', 'In Progress'),
            ('Tran Thi B', 'Logistics', 'Missing safety gear', 'Security Gate', NOW() - INTERVAL '20 days', 'Resolved'),
            ('Tran Thi B', 'Logistics', 'Improper conduct', 'Logistics Hub', NOW() - INTERVAL '5 days', 'In Progress'),
            ('Le Van C', 'Production', 'Arriving late', 'Workshop Floor', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Le Van C', 'Production', 'Missing safety gear', 'Workshop Floor', NOW() - INTERVAL '3 days', 'Resolved'),
            ('Le Van C', 'Production', 'Improper conduct', 'Office Zone', NOW(), 'In Progress'),
            ('Pham Van D', 'Maintenance', 'Missing safety gear', 'Logistics Hub', NOW() - INTERVAL '7 days', 'Resolved'),
            ('Hoang Thi E', 'Logistics', 'Missing safety gear', 'Logistics Hub', NOW() - INTERVAL '4 days', 'Resolved'),
            ('Vu Van F', 'Production', 'Operational violation', 'Workshop Floor', NOW() - INTERVAL '6 days', 'In Progress'),
            ('Dang Thi H', 'Production', 'Missing safety gear', 'Construction Zone', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Bui Van G', 'Construction', 'Missing safety gear', 'Construction Zone', NOW() - INTERVAL '2 hours', 'In Progress'),
            ('Tran Minh G', 'Security', 'Improper conduct', 'Security Gate', NOW() - INTERVAL '8 hours', 'In Progress'),
            ('Ly Thi K', 'Office', 'Improper conduct', 'Office Zone', NOW() - INTERVAL '1 day', 'Resolved'),
            ('Ho Van M', 'Production', 'Smoking violation', 'Workshop Floor', NOW() - INTERVAL '3 days', 'In Progress'),
            ('Doan Chi N', 'Logistics', 'Improper conduct', 'Logistics Hub', NOW() - INTERVAL '5 days', 'Resolved'),
            ('Ngo Quyen P', 'Sales', 'Missing safety gear', 'Office Zone', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Duong Qua T', 'Production', 'Missing safety gear', 'Workshop Floor', NOW() - INTERVAL '2 days', 'Resolved'),
            ('Truong Vo Ky', 'IT', 'Operational violation', 'Office Zone', NOW() - INTERVAL '1 hour', 'In Progress'),
            ('Chu Chi Nhuoc', 'HR', 'Improper conduct', 'Office Zone', NOW() - INTERVAL '4 days', 'Resolved');
        """))
        
    print("Database reset complete. Tables 'violations', 'chat_sessions', and 'chat_messages' are ready.")

if __name__ == "__main__":
    setup_database()