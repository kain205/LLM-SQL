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
    Drops the existing 'violations' table and recreates it with fresh sample data.
    This is useful for development to reset the database to a known state.
    """
    print("Resetting database...")
    with engine.begin() as conn:
        # Drop the table if it exists to ensure a clean slate
        print("Dropping table 'public.violations' if it exists...")
        conn.execute(text("DROP TABLE IF EXISTS public.violations CASCADE;"))

        # Create the table
        print("Creating 'violations' table on Supabase (Postgres)...")
        conn.execute(text("""
            CREATE TABLE public.violations (
                id SERIAL PRIMARY KEY,
                employee_name TEXT NOT NULL,
                violation_type TEXT,
                violation_date DATE,
                status TEXT
            );
        """))

        # Insert fresh sample data
        print("Inserting sample data...")
        conn.execute(text("""
            INSERT INTO public.violations (employee_name, violation_type, violation_date, status) VALUES
            -- Original Data
            ('Nguyen Van A', 'Đi trễ', CURRENT_DATE, 'pending'),
            ('Tran Thi B', 'Không mặc đồng phục', CURRENT_DATE - INTERVAL '7 day', 'resolved'),
            ('Le Van C', 'Đi trễ', CURRENT_DATE, 'pending'),

            -- New Computer Vision Data
            ('Phạm Văn D', 'Không đội mũ bảo hiểm', CURRENT_DATE - INTERVAL '1 day', 'pending'),
            ('Hoàng Thị E', 'Thiếu mũ bảo hộ', CURRENT_DATE - INTERVAL '2 day', 'resolved'),
            ('Vũ Văn F', 'không đội nón bảo hiểm tại công trường', CURRENT_DATE, 'pending'),
            ('Trần Minh G', 'Không mặc áo bảo hộ', CURRENT_DATE - INTERVAL '3 day', 'investigating'),
            ('Lê Thị H', 'Thiếu áo phản quang', CURRENT_DATE - INTERVAL '4 day', 'resolved'),
            ('Nguyễn Anh I', 'Sử dụng điện thoại khi vận hành máy', CURRENT_DATE, 'pending'),
            ('Đặng Văn K', 'Nghe điện thoại trong giờ làm việc', CURRENT_DATE - INTERVAL '5 day', 'resolved'),
            ('Bùi Thị L', 'Đi vào khu vực cấm', CURRENT_DATE - INTERVAL '1 day', 'investigating'),
            ('Hồ Văn M', 'Xâm nhập vùng nguy hiểm', CURRENT_DATE, 'pending'),
            ('Doãn Chí N', 'Đỗ xe sai quy định', CURRENT_DATE - INTERVAL '10 day', 'resolved'),
            ('Ngô Quyền P', 'đậu xe lấn chiếm lối đi', CURRENT_DATE - INTERVAL '2 day', 'pending'),
            ('Dương Quá T', 'Hút thuốc nơi cấm', CURRENT_DATE - INTERVAL '6 day', 'resolved'),
            ('Lý Mạc Sầu U', 'hút thuốc lá trong nhà xưởng', CURRENT_DATE - INTERVAL '1 day', 'pending'),
            ('Trương Vô Kỵ', 'Không đeo khẩu trang', CURRENT_DATE, 'investigating'),
            ('Chu Chỉ Nhược', 'thiếu khẩu trang y tế', CURRENT_DATE - INTERVAL '3 day', 'resolved');
        """))
        
    print("Database reset complete. Table 'violations' is ready.")

if __name__ == "__main__":
    setup_database()