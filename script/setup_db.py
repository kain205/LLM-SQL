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
            ('Nguyen Van A', 'Production', 'Arriving late', 'Workshop A', NOW() - INTERVAL '15 days', 'Resolved'),
            ('Nguyen Van A', 'Production', 'Not wearing uniform', 'Workshop A', NOW() - INTERVAL '10 days', 'Resolved'),
            ('Nguyen Van A', 'Production', 'Using phone during work hours', 'Rest Area', NOW() - INTERVAL '2 days', 'In Progress'),
            ('Tran Thi B', 'Logistics', 'Not wearing helmet', 'Gate 2', NOW() - INTERVAL '20 days', 'Resolved'),
            ('Tran Thi B', 'Logistics', 'Improper parking', 'Parking Lot', NOW() - INTERVAL '5 days', 'In Progress'),
            ('Le Van C', 'Production', 'Arriving late', 'Workshop B', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Le Van C', 'Production', 'Not wearing safety gloves', 'Workshop B', NOW() - INTERVAL '3 days', 'Resolved'),
            ('Le Van C', 'Production', 'Causing a disturbance', 'Cafeteria', NOW(), 'In Progress'),

            ('Pham Van D', 'Maintenance', 'Not using safety helmet', 'Technical Room', NOW() - INTERVAL '7 days', 'Resolved'),
            ('Hoang Thi E', 'Logistics', 'Missing reflective vest', 'Corridor B', NOW() - INTERVAL '4 days', 'Resolved'),
            ('Vu Van F', 'Production', 'Improper machine operation', 'Workshop A', NOW() - INTERVAL '6 days', 'In Progress'),
            ('Dang Thi H', 'Production', 'Missing helmet at construction site', 'Construction Site X', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Bui Van G', 'Construction', 'Not wearing safety harness at height', '5th Floor, Building A', NOW() - INTERVAL '2 hours', 'In Progress'),

            ('Tran Minh G', 'Security', 'Leaving post', 'Gate 1', NOW() - INTERVAL '8 hours', 'In Progress'),
            ('Ly Thi K', 'Office', 'Eating at desk', 'Office Area', NOW() - INTERVAL '1 day', 'Resolved'),
            ('Ho Van M', 'Production', 'Smoking in the workshop', 'Workshop C', NOW() - INTERVAL '3 days', 'In Progress'),
            ('Doan Chi N', 'Logistics', 'Parking in a restricted area', 'Warehouse Aisle', NOW() - INTERVAL '5 days', 'Resolved'),
            
            ('Ngo Quyen P', 'Sales', 'Not wearing name tag', 'Meeting Room', NOW() - INTERVAL '1 day', 'In Progress'),
            ('Duong Qua T', 'Production', 'Wearing incorrect uniform', 'Workshop A', NOW() - INTERVAL '2 days', 'Resolved'),

            ('Truong Vo Ky', 'IT', 'Accessing forbidden websites', 'IT Office', NOW() - INTERVAL '1 hour', 'In Progress'),
            ('Chu Chi Nhuoc', 'HR', 'Unexcused absence', 'HR Office', NOW() - INTERVAL '4 days', 'Resolved');
        """))
        
    print("Database reset complete. Table 'violations' is ready.")

if __name__ == "__main__":
    setup_database()