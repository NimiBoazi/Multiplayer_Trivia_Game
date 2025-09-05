import random
import pandas as pd
from typing import List, Dict, Any, Optional
from . import config

# Load questions DataFrame once
try:
    questions_df = pd.read_csv(config.QUESTIONS_CSV_FILE)
except FileNotFoundError:
    raise SystemExit(f"Error: {config.QUESTIONS_CSV_FILE} not found.")


def get_random_questions(num: int, diff: Optional[int] = None, tol: int = 1) -> List[Dict[str, Any]]:
    global questions_df
    if questions_df is None or questions_df.empty:
        print("Error: questions_df is not loaded or is empty. Cannot get random questions.")
        return []

    available_questions = questions_df.copy()
    if diff is not None:
        min_d, max_d = max(1, diff - tol), min(10, diff + tol)
        filtered = available_questions[(available_questions['Difficulty'] >= min_d) & (available_questions['Difficulty'] <= max_d)]
        if len(filtered) >= num:
            available_questions = filtered
        elif not filtered.empty:
            available_questions = filtered

    if available_questions.empty:
        print("Warning: No questions available for sampling (possibly after filtering).")
        return []

    sample_n = min(num, len(available_questions))
    if sample_n == 0:
        return []

    needs_replacement = len(available_questions) < num
    selected_df = available_questions.sample(n=sample_n, replace=needs_replacement)

    q_list = []
    for _, row in selected_df.iterrows():
        try:
            options = [row['Correct Answer'], row['Wrong Answer 1'], row['Wrong Answer 2'], row['Wrong Answer 3']]
            random.shuffle(options)
            q_list.append({
                'question': row['Question'],
                'options': options,
                'correct_answer': row['Correct Answer'],
                'difficulty': int(row['Difficulty'])
            })
        except KeyError as e:
            print(f"Error processing question row (missing key {e}): {row.to_dict()}")
            continue
    return q_list

