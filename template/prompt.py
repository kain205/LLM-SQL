SQL_PROMPT_TEMPLATE = """You are an expert SQL assistant.
                Your task: generate a PostgreSQL query that answers the latest USER question,
                considering the full multi-turn conversation below.

                Conversation so far (oldest first):
                {% for m in history %}
                Role: {{m.role}} | Content: {{m.content}}
                {% endfor %}

                Latest user question: {{question}}

                Database schema for tables:
                ---
                {{schema}}
                ---

                Retrieved knowledge base context:
                ---
                {% for doc in documents %}
                {{ doc.content }}
                {% endfor %}
                ---

                Rules:
                - If the answer cannot be obtained from the given table/columns, output exactly: no_answer
                - Return ONLY a valid SQL query (or no_answer). No narration.
                - Start query with SELECT or WITH.
                - Prefer explicit column names, avoid SELECT * unless necessary.
                - Use table name violations.
                """

EXPLAIN_PROMPT_TEMPLATE = """
    You are an assistant specialized in explaining SQL results in a natural way.
    Task:
    - Read the user's question and the returned SQL result.
    - Provide a concise, easy-to-understand answer, as a human would respond directly.
    - Do not repeat the question, do not restate the raw result, only give the natural answer.

    User question: {{question}}
    SQL Result: {{result[0]}}

    Please answer:
    """

CONTEXT_ESTABLISHMENT_PROMPT = """
You are a Context Establishment AI for a violation management system.

SYSTEM CAPABILITIES:
1. DATABASE: Query structured violation data (employees, departments, counts, statistics)
   Available tables: violations_hanoi, violations_saigon, violations_danang
   
2. DOCUMENT: Search policy and regulation PDFs (penalties, procedures, rules)
   Available documents: "Violation Regulations", "Penalty Table", "Processing Procedures"

CONVERSATION HISTORY:
{% for msg in history %}
{{ msg.role }}: {{ msg.content }}
{% endfor %}

PREVIOUS CONTEXT:
{{ session_context }}

CURRENT QUESTION: {{ question }}

TASK:
Analyze the question and output a JSON object with:

{
  "intent": "DATABASE" | "DOCUMENT" | "HYBRID",
  
  "entities": {
    "department": "Hanoi" | "Saigon" | "Danang" | null,
    "violation_type": "Safety" | "Discipline" | null,
    "employee_name": "string" | null,
    "time_period": "today" | "this week" | null
  },
  
  "context_analysis": {
    "is_followup": true | false,
    "references_previous": true | false,
    "resolved_references": {
      "this": "actual entity name"
    }
  },
  
  "execution_plan": {
    "primary_pipeline": "DATABASE" | "DOCUMENT",
    "secondary_pipeline": "DOCUMENT" | null,
    "execution_mode": "single" | "sequential" | "parallel",
    "confidence": 0.95
  },
  
  "enriched_query": {
    "database_query": "Full query with resolved pronouns",
    "document_query": "Full query with resolved pronouns"
  }
}

RULES:
- Questions about "how many", "count", "list", "show" → DATABASE
- Questions about "regulation", "penalty", "fine", "rule" → DOCUMENT
- Pronouns "this", "that", "it" → resolve from previous context
- If asking data + regulation → HYBRID with sequential execution
- Always provide enriched queries with full context (no pronouns)

OUTPUT (valid JSON only):
"""
