import pandas as pd
import google.generativeai as genai
import os
import random
import time
from dotenv import load_dotenv

# --- Configuration ---
CSV_INPUT_FILE = "trivia_questions.csv"
CSV_OUTPUT_FILE = "trivia_questions_filtered.csv"
BATCH_SIZE = 10 # Number of questions to send to the LLM at once
MODEL_NAME = "gemini-1.5-flash-latest" # Use the specific model ID if "Gemini 2.0 Flash" is different

# Safety settings for the LLM (can be adjusted)
GENERATION_CONFIG = {
    "temperature": 0.1, # Lower temperature for more deterministic answers
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024, # Should be enough for BATCH_SIZE answers
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Helper Functions ---
def load_api_key():
    """Loads Google API key from .env file."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file or environment variables.")
    return api_key

def format_question_for_llm(index, question_data):
    """
    Formats a single question and its shuffled answers for the LLM.
    Returns the formatted string and the list of shuffled answers.
    """
    question = question_data["Question"]
    correct_answer = question_data["Correct Answer"]
    wrong_answers = [
        question_data["Wrong Answer 1"],
        question_data["Wrong Answer 2"],
        question_data["Wrong Answer 3"],
    ]

    all_answers = [correct_answer] + wrong_answers
    random.shuffle(all_answers) # Shuffle the answers

    options_str = ""
    for i, ans in enumerate(all_answers):
        options_str += f"  {chr(65 + i)}. {ans}\n" # A, B, C, D

    formatted_q = f"Question {index + 1}:\n{question}\n{options_str}Your Answer (letter only):"
    return formatted_q, all_answers


def ask_gemini_batch(model, questions_batch_data):
    """
    Sends a batch of formatted questions to Gemini and gets answers.
    questions_batch_data is a list of tuples: (original_index, question_row_data)
    Returns a list of (original_index, llm_chosen_answer_text, correct_answer_text)
    """
    prompt_parts = [
        "You are a trivia answering AI. For each question below, provide only the letter (A, B, C, D, or E) corresponding to your chosen answer. Each answer should be on a new line. Do not add any other text, explanations, or greetings."
    ]
    
    # Store shuffled options for each question in the batch to map LLM's letter back
    batch_shuffled_options_map = {} # key: batch_q_idx, value: list_of_shuffled_answers

    for i, (original_idx, q_data) in enumerate(questions_batch_data):
        formatted_q_str, shuffled_answers = format_question_for_llm(i, q_data)
        prompt_parts.append(f"\n---\n{formatted_q_str}")
        batch_shuffled_options_map[i] = shuffled_answers
        
    full_prompt = "\n".join(prompt_parts)
    
    print("\n--- Sending to Gemini ---")
    print(full_prompt)
    print("-------------------------\n")

    try:
        response = model.generate_content(
            full_prompt,
            generation_config=GENERATION_CONFIG,
            safety_settings=SAFETY_SETTINGS
        )
        llm_raw_answers = response.text.strip().split('\n')
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # In case of API error, we assume LLM failed all questions in this batch
        # Or you could implement retries or other error handling
        return [(data[0], None, data[1]["Correct Answer"]) for data in questions_batch_data]


    results = []
    if len(llm_raw_answers) != len(questions_batch_data):
        print(f"Warning: Mismatch in number of answers received from LLM ({len(llm_raw_answers)}) and questions sent ({len(questions_batch_data)}). Marking all as incorrect for this batch.")
        for original_idx, q_data in questions_batch_data:
            results.append((original_idx, None, q_data["Correct Answer"])) # None indicates LLM failed to answer correctly
        return results

    for i, (original_idx, q_data) in enumerate(questions_batch_data):
        llm_answer_letter = llm_raw_answers[i].strip().upper()
        shuffled_options = batch_shuffled_options_map[i]
        llm_chosen_answer_text = None

        if len(llm_answer_letter) == 1 and 'A' <= llm_answer_letter <= 'E':
            option_index = ord(llm_answer_letter) - ord('A')
            if 0 <= option_index < len(shuffled_options):
                llm_chosen_answer_text = shuffled_options[option_index]
            else:
                print(f"Warning: LLM returned an invalid option letter '{llm_answer_letter}' for question index {original_idx}. Original Q: {q_data['Question']}")
        else:
            print(f"Warning: LLM returned an unexpected format '{llm_raw_answers[i]}' for question index {original_idx}. Original Q: {q_data['Question']}")
        
        results.append((original_idx, llm_chosen_answer_text, q_data["Correct Answer"]))
        
    return results


# --- Main Script ---
def main():
    print("Starting trivia question filtering process...")

    # 1. Load API Key
    try:
        api_key = load_api_key()
        genai.configure(api_key=api_key)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # 2. Initialize Gemini Model
    model = genai.GenerativeModel(
        MODEL_NAME,
        # safety_settings=SAFETY_SETTINGS, # Passed during generation
        # generation_config=GENERATION_CONFIG # Passed during generation
    )
    print(f"Gemini model '{MODEL_NAME}' initialized.")

    # 3. Load CSV
    try:
        df = pd.read_csv(CSV_INPUT_FILE)
        print(f"Loaded {len(df)} questions from '{CSV_INPUT_FILE}'.")
    except FileNotFoundError:
        print(f"Error: Input CSV file '{CSV_INPUT_FILE}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if df.empty:
        print("Input CSV is empty. Nothing to process.")
        return

    # Make a copy to modify, or work on the original if preferred
    df_filtered = df.copy()
    indices_to_delete = []

    # 4. Process questions in batches
    num_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Processing in {num_batches} batches of size {BATCH_SIZE}.")

    for i in range(0, len(df), BATCH_SIZE):
        batch_df = df.iloc[i:i + BATCH_SIZE]
        
        # Prepare batch data as list of (original_index, row_data_dict)
        questions_batch_data = []
        for original_idx, row in batch_df.iterrows():
            questions_batch_data.append((original_idx, row.to_dict()))

        print(f"\nProcessing batch {i // BATCH_SIZE + 1}/{num_batches} (questions {i+1}-{min(i+BATCH_SIZE, len(df))})...")
        
        batch_results = ask_gemini_batch(model, questions_batch_data)

        for original_idx, llm_answer, correct_answer in batch_results:
            question_text = df.loc[original_idx, "Question"]
            is_correct = llm_answer is not None and str(llm_answer).strip().lower() == str(correct_answer).strip().lower()
            
            if is_correct:
                print(f"  Q (idx {original_idx}): CORRECT. LLM answered '{llm_answer}'.")
            else:
                print(f"  Q (idx {original_idx}): INCORRECT. LLM answered '{llm_answer}', Correct was '{correct_answer}'. Marking for deletion.")
                print(f"     Question: {question_text[:80]}...") # Print a snippet of the question
                indices_to_delete.append(original_idx)
        
        if i // BATCH_SIZE + 1 < num_batches: # Avoid sleeping after the last batch
            print(f"Waiting for 5 seconds before next batch to respect API rate limits...")
            time.sleep(5) # Add a small delay to avoid hitting rate limits too quickly

    # 5. Delete incorrect questions
    if indices_to_delete:
        print(f"\nDeleting {len(indices_to_delete)} questions marked as too hard.")
        df_filtered.drop(indices_to_delete, inplace=True)
        df_filtered.reset_index(drop=True, inplace=True) # Good practice after dropping
    else:
        print("\nNo questions were marked for deletion.")

    # 6. Save the filtered CSV
    try:
        df_filtered.to_csv(CSV_OUTPUT_FILE, index=False)
        print(f"\nFiltered questions saved to '{CSV_OUTPUT_FILE}'.")
        print(f"Original questions: {len(df)}, Filtered questions: {len(df_filtered)}.")
    except Exception as e:
        print(f"Error saving filtered CSV: {e}")

    print("\nProcess completed.")

if __name__ == "__main__":
    main()