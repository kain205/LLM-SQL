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
                employee_name TEXT,
                department TEXT,
                violation_type TEXT,
                area TEXT,
                violation_time TIMESTAMP,
                status TEXT
            );
        """))

        # Insert fresh sample data
        print("Inserting sample data...")
        conn.execute(text("""
            INSERT INTO public.violations (employee_name, department, violation_type, area, violation_time, status) VALUES
            -- Frequent violators
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
        
    print("Database reset complete. Table 'violations' is ready.")

if __name__ == "__main__":
    setup_database()