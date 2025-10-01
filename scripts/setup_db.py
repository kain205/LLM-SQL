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
    Drops existing tables and recreates them with the correct schema,
    including a master 'departments' table and the foreign key relationship.
    """
    print("Resetting database...")
    with engine.begin() as conn:
        # --- PART 1: DROP ALL TABLES ---
        # Dropping with CASCADE handles dependencies correctly.
        print("Dropping all tables if they exist...")
        conn.execute(text("DROP TABLE IF EXISTS public.violations CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS public.chat_messages CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS public.chat_sessions CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS public.departments CASCADE;")) # -- NEW --

        # --- PART 2: RECREATE TABLES ---
        # -- NEW --: Create the master 'departments' table first.
        print("Creating 'departments' table...")
        conn.execute(text("""
            CREATE TABLE public.departments (
                department_name TEXT PRIMARY KEY
            );
        """))

        # -- MODIFIED --: Create the 'violations' table with a foreign key.
        print("Creating 'violations' table...")
        conn.execute(text("""
            CREATE TABLE public.violations (
                id SERIAL PRIMARY KEY,
                employee_name TEXT,
                department TEXT REFERENCES public.departments(department_name), -- MODIFIED --
                violation_type TEXT,
                area TEXT,
                violation_time TIMESTAMP,
                status TEXT
            );
        """))

        # Create chat tables (unchanged)
        print("Creating 'chat_sessions' table...")
        conn.execute(text("""
            CREATE TABLE public.chat_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            );
        """))
        
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

        # --- PART 3: INSERT SAMPLE DATA ---
        # -- NEW --: Populate the 'departments' table.
        # This includes all departments from your original data, plus two extra for testing.
        print("Inserting sample data for 'departments'...")
        conn.execute(text("""
            INSERT INTO public.departments (department_name) VALUES
            ('Production'),
            ('Logistics'),
            ('Maintenance'),
            ('Construction'),
            ('Security'),
            ('Office'),
            ('Sales'),
            ('IT'),
            ('HR'),
            ('R&D'),          -- For testing "no violations"
            ('Marketing');    -- For testing "no violations"
        """))

        # Your original violations data is unchanged.
        print("Inserting sample data for 'violations'...")
        conn.execute(text("""
            INSERT INTO public.violations (employee_name, department, violation_type, area, violation_time, status) VALUES
            ('Nguyen Van A', 'Production', 'Arriving late', 'Workshop Floor', NOW() - INTERVAL '15 days', 'Resolved'),
            ('Nguyen Van A', 'Production', 'Missing safety gear', 'Workshop Floor', NOW() - INTERVAL '10 days', 'Resolved'),
            ('Nguyen Van A', 'Production', 'Missing safety gear', 'Workshop Floor', NOW() - INTERVAL '8 days', 'Resolved'),  -- Same violation type again
            ('Nguyen Van A', 'Production', 'Improper conduct', 'Office Zone', NOW() - INTERVAL '2 days', 'In Progress'),
            ('Tran Thi B', 'Logistics', 'Missing safety gear', 'Security Gate', NOW() - INTERVAL '20 days', 'Resolved'),
            ('Tran Thi B', 'Logistics', 'Improper conduct', 'Logistics Hub', NOW() - INTERVAL '5 days', 'In Progress'),
            ('Tran Thi B', 'Logistics', 'Improper conduct', 'Logistics Hub', NOW() - INTERVAL '3 days', 'Resolved'),  -- Same violation type again
            ('Le Van C', 'Production', 'Arriving late', 'Workshop Floor', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Le Van C', 'Production', 'Missing safety gear', 'Workshop Floor', NOW() - INTERVAL '3 days', 'Resolved'),
            ('Le Van C', 'Production', 'Improper conduct', 'Office Zone', NOW(), 'In Progress'),
            ('Pham Van D', 'Maintenance', 'Missing safety gear', 'Logistics Hub', NOW() - INTERVAL '7 days', 'Resolved'),
            ('Pham Van D', 'Maintenance', 'Missing safety gear', 'Logistics Hub', NOW() - INTERVAL '5 days', 'Resolved'),  -- Same violation type again
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
        
    print("Database reset complete. All tables are ready.")

if __name__ == "__main__":
    setup_database()