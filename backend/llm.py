import os
from . import config

_gemini_model_instance = None
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    genai = None
    HarmCategory = HarmBlockThreshold = None


def get_gemini_model():
    global _gemini_model_instance
    if _gemini_model_instance is None:
        if not genai:
            return None
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                generation_config = genai.types.GenerationConfig(candidate_count=1, max_output_tokens=150, temperature=0.8)
                _gemini_model_instance = genai.GenerativeModel(config.LLM_MODEL_TO_USE, safety_settings=safety_settings, generation_config=generation_config)
                print(f"Gemini model ({config.LLM_MODEL_TO_USE}) initialized.")
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
                _gemini_model_instance = None
        else:
            print("GOOGLE_API_KEY not found.")
            _gemini_model_instance = None
    return _gemini_model_instance


def get_llm_advice(q_txt, opts):
    model = get_gemini_model()
    if not model:
        return "AI friend unavailable."
    prmpt = f"Trivia Hint: Q:\"{q_txt}\" Opts:{opts}. Fun, subtle hint (1-2 sent.), not direct answer."
    try:
        resp = model.generate_content(prmpt)
        if getattr(resp, 'candidates', None) and getattr(resp, 'text', None):
            adv = resp.text.strip().replace("**", "")
            if not adv or "unable" in adv or "cannot" in adv:
                return "AI friend uninspired!"
            return adv
        if getattr(resp, 'prompt_feedback', None) and getattr(resp.prompt_feedback, 'block_reason', None):
            return "AI friend blocked!"
        return "AI friend odd reply."
    except Exception as e:
        print(f"Gemini Call Fail: {e}")
        return "AI connection fuzzy!"

