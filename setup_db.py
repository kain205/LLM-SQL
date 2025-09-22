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
                ten_nhan_vien TEXT,
                phong_ban TEXT,
                loai_vi_pham TEXT,
                khu_vuc TEXT,
                thoi_gian_vi_pham TIMESTAMP,
                trang_thai TEXT
            );
        """))

        # Insert fresh sample data
        print("Inserting sample data...")
        conn.execute(text("""
            INSERT INTO public.violations (ten_nhan_vien, phong_ban, loai_vi_pham, khu_vuc, thoi_gian_vi_pham, trang_thai) VALUES
            -- Người vi phạm nhiều lần
            ('Nguyen Van A', 'Sản xuất', 'Đi trễ', 'Xưởng A', NOW() - INTERVAL '15 days', 'Đã giải quyết'),
            ('Nguyen Van A', 'Sản xuất', 'Không mặc đồng phục', 'Xưởng A', NOW() - INTERVAL '10 days', 'Đã giải quyết'),
            ('Nguyen Van A', 'Sản xuất', 'Sử dụng điện thoại trong giờ', 'Khu vực nghỉ', NOW() - INTERVAL '2 days', 'Đang xử lý'),
            ('Tran Thi B', 'Kho vận', 'Không đội mũ bảo hiểm', 'Cổng số 2', NOW() - INTERVAL '20 days', 'Đã giải quyết'),
            ('Tran Thi B', 'Kho vận', 'Để xe sai quy định', 'Bãi xe', NOW() - INTERVAL '5 days', 'Đang xử lý'),
            ('Le Van C', 'Sản xuất', 'Đi làm muộn', 'Xưởng B', NOW() - INTERVAL '1 day', 'Đang xử lý'),
            ('Le Van C', 'Sản xuất', 'Không đeo găng tay bảo hộ', 'Xưởng B', NOW() - INTERVAL '3 days', 'Đã giải quyết'),
            ('Le Van C', 'Sản xuất', 'Gây mất trật tự', 'Nhà ăn', NOW(), 'Đang xử lý'),

            ('Phạm Văn D', 'Bảo trì', 'Không sử dụng nón bảo hộ', 'Phòng kỹ thuật', NOW() - INTERVAL '7 days', 'Đã giải quyết'),
            ('Hoàng Thị E', 'Kho vận', 'Thiếu áo phản quang', 'Hành lang B', NOW() - INTERVAL '4 days', 'Đã giải quyết'),
            ('Vũ Văn F', 'Sản xuất', 'Vận hành máy không đúng quy trình', 'Xưởng A', NOW() - INTERVAL '6 days', 'Đang xử lý'),
            ('Đặng Thị H', 'Sản xuất', 'thiếu mũ bảo hiểm tại công trường', 'Công trường X', NOW() - INTERVAL '1 day', 'Đang xử lý'),
            ('Bùi Văn G', 'Xây dựng', 'Không thắt dây an toàn khi làm việc trên cao', 'Tầng 5, Tòa nhà A', NOW() - INTERVAL '2 hours', 'Đang xử lý'),

            ('Trần Minh G', 'An ninh', 'Bỏ vị trí gác', 'Cổng số 1', NOW() - INTERVAL '8 hours', 'Đang xử lý'),
            ('Lý Thị K', 'Văn phòng', 'Ăn uống tại bàn làm việc', 'Khu văn phòng', NOW() - INTERVAL '1 day', 'Đã giải quyết'),
            ('Hồ Văn M', 'Sản xuất', 'hút thuốc lá trong nhà xưởng', 'Xưởng C', NOW() - INTERVAL '3 days', 'Đang xử lý'),
            ('Doãn Chí N', 'Kho vận', 'đậu xe lấn chiếm lối đi', 'Lối đi kho', NOW() - INTERVAL '5 days', 'Đã giải quyết'),
            
            ('Ngô Quyền P', 'Kinh doanh', 'Không đeo thẻ tên', 'Phòng họp', NOW() - INTERVAL '1 day', 'Đang xử lý'),
            ('Dương Quá T', 'Sản xuất', 'Mặc sai đồng phục quy định', 'Xưởng A', NOW() - INTERVAL '2 days', 'Đã giải quyết'),

            ('Trương Vô Kỵ', 'IT', 'Truy cập trang web cấm', 'Văn phòng IT', NOW() - INTERVAL '1 hour', 'Đang xử lý'),
            ('Chu Chỉ Nhược', 'Nhân sự', 'Vắng mặt không lý do', 'Văn phòng nhân sự', NOW() - INTERVAL '4 days', 'Đã giải quyết');
        """))
        
    print("Database reset complete. Table 'violations' is ready.")

if __name__ == "__main__":
    setup_database()