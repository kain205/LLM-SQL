# 📊 LLM SQL Model Test & Report

> This file is used to record test questions and report the results of model evaluation on the violations database. Test on new RAG
>
> **Models being tested:**
> - A: `hf.co/second-state/CodeQwen1.5-7B-Chat-GGUF:Q4_K_M`
> - B: `gemini-flash`
> - C: `<add model name>`
>
> **Quick guide:**
> - Run the pipeline with each question below for all models.
> - For each question, record:
>   - Model A: [SQL | Result | Evaluation]
>   - Model B: [SQL | Result | Evaluation]
>   - Model C: [SQL | Result | Evaluation]
> - You can attach the `report.html` link or quote from `logs/results.jsonl`.

---

## 📝 Test Questions Set

### 1) Basic Queries
1. How many violations are recorded in the system?
    - Model A: OK
    - Model B: OK
    - Model C: Pending

2. Who has the most violations?
    - Model A: Generated incorrect SQL
    - Model B: Generated incorrect SQL
    - Model C: Pending

3. List all types of violations in the system.
    - Model A: OK
    - Model B: OK
    - Model C: Pending

4. How many violations are in "Processing" status?
    - Model A: OK
    - Model B: OK
    - Model C: Pending

5. List employees from the "Production" department.
    - Model A: Generated incorrect SQL
    - Model B: OK
    - Model C: Pending

### 2) Time Filtering
6. What violations occurred this week?
    - Model A: Generated SQL for the last 7 days instead of this week
    - Model B: OK
    - Model C: Pending

7. List the violations from last month.
    - Model A: OK
    - Model B: OK
    - Model C: Pending

8. Which day had the most violations?
    - Model A: OK
    - Model B: OK
    - Model C: Pending

9. What was the most recent violation?
    - Model A: OK
    - Model B: OK
    - Model C: Pending

10. How many violations occurred in the first quarter of the year?
    - Model A: Generated incorrected SQL
    - Model B: OK
    - Model C: Pending

### 3) Aggregations & Analytics
11. Count the number of violations by department.
    - Model A: OK
    - Model B: OK
    - Model C: Pending

12. Which department has the highest rate of "Resolved" violations?
    - Model A: Generated incorrect SQL
    - Model B: OK
    - Model C: Pending

13. What is the most common type of violation in "Workshop A"?
    - Model A: Generated incorrect SQL
    - Model B: Generated incorrect SQL
    - Model C: Pending
    - Note: There are multiple violation types with the same highest count. Lacks the ability to handle tie cases.

14. Compare the number of violations between "Workshop A" and "Workshop B".
    - Model A: Generated faulty SQL
    - Model B: OK
    - Model C: Pending

15. Which area has the most violations?
    - Model A: OK
    - Model B: OK
    - Model C: Pending

### 4) Complex Queries
16. Which employee has committed violations in the most different areas?
    - Model A: Generated incorrect SQL
    - Model B: Generated incorrect SQL
    - Model C: Generated incorrect SQL
    - Note: Similar to question 13, the model cannot handle tie cases.

17. List employees who have committed at least 3 violations and have at least 1 violation "In Progress".
    - Model A: Generated faulty SQL
    - Model B: OK
    - Model C: Pending

18. What is the resolution rate of violations for each department?
    - Model A: Generated incorrect SQL
    - Model B: OK
    - Model C: Pending

19. Which employees have committed violations in both the office and production areas?
    - Model A: Generated incorrect SQL
    - Model B: Generated incorrect SQL
    - Model C: Pending
    - Note: The "office" and "production" areas are not clearly defined. There are multiple interpretations of these terms, so the model cannot handle it.

20. What is the average time from when a violation occurs until it is resolved?
    - Model A: Generated faulty SQL
    - Model B: Correctly answered "no_answer" for cases where the model is uncertain.
    - Model C: Pending
    - Note: This data is not available in the database.

### 5) Edge Cases & Special Tests
21. Has anyone committed the same error multiple times?
    - Model A: Generated incorrect SQL
    - Model B: OK
    - Model C: Pending

22. List violations that occurred on the weekend.
    - Model A: OK
    - Model B: OK
    - Model C: Pending

23. Who is the only person to have violated the "smoking in the workshop" rule?
    - Model A: Generated incorrect SQL
    - Model B: Generated incorrect SQL because it did not capitalize a letter in the query.
    - Model C: Pending

24. Are there any departments with no violations?
    - Model A: Answered despite having no information.
    - Model B: Correctly answered "no_answer" because there is no information.
    - Model C: Pending

25. What time of day do violations most often occur?
    - Model A: OK
    - Model B: OK
    - Model C: OK

---

## 📎 General Report
- Report HTML: ./report.html (fill in the link if built)
- Detailed log: ./logs/results.jsonl
- Quick summary:
    - Correct answers: A __ | B __ | C __
    - Incorrect/no answers: A __ | B __ | C __
    - Valid SQL: A __% | B __% | C __%
    - Average time: A __s | B __s | C __s
    - General evaluation:
        - Model A (CodeQwen):
        - Model B (Gemini Flash):
        - Model C (<add name>):
- Notes for model improvement:
