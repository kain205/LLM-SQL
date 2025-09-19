# LLM Text-to-SQL for Violation Tracking

This project is a Streamlit web application that allows users to ask questions in natural language about a database of workplace violations. It uses a Large Language Model (LLM) via the Haystack framework to convert user questions into SQL queries, execute them against a Supabase (PostgreSQL) database, and return the answers in a user-friendly format.

## Features

*   **Natural Language to SQL:** Ask questions like "How many people were late today?" and get answers directly from the database.
*   **Streamlit UI:** A simple and interactive web interface to view data and ask questions.
*   **Supabase Integration:** Connects to a PostgreSQL database hosted on Supabase.
*   **Dynamic Context:** Automatically provides the LLM with table schema, sample data, and distinct values to improve query generation accuracy.
*   **Interaction Logging:** Logs user questions, generated SQL, and results for debugging and analysis.

## Requirements

*   Python 3.11.13
*   A Supabase account (or any PostgreSQL database)
*   A Google AI API Key

## Setup and Installation

1.  **Clone the repository (optional):**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-folder>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a file named `.env` in the project root and add the following, replacing the placeholder values with your actual credentials:
    ```env
    # Your Supabase/PostgreSQL connection string
    DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@[db.xxxxxxxx.supabase.co]:5432/postgres"

    # Your Google AI API Key
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    ```

## Usage

1.  **Set up the database:**
    Run the setup script to create the `violations` table and populate it with sample data.
    ```bash
    python setup_db.py
    ```

2.  **Run the Streamlit application:**
    ```bash
    streamlit run app.py
    ```

3.  Open your web browser to the local URL provided by Streamlit (usually `http://localhost:8501`).

## File Structure

*   `app.py`: The main Streamlit application file containing the UI and Haystack pipeline logic.
*   `setup_db.py`: A script to initialize the database by creating and populating the `violations` table.
*   `requirements.txt`: A list of all Python libraries required for the project.
*   `.env`: Stores environment variables like database credentials and API keys (not committed to version control).
*   `app_log.json`: A log file that records all user interactions with the application.
*   `README.md`: This file.
