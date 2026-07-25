from config.llm_factory import get_llm

llm = get_llm()

def format_for_platforms(jd_text):
    prompt = f"""
Format the following job description for:

1. LinkedIn
2. Indeed
3. Career Page

Provide clearly separated sections.

JD:
{jd_text}
"""
    return llm.invoke(prompt).content
