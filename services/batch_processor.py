from agents.resume_agent import parse_resume
from agents.screening_agent import screen_candidate

"""This function takes a job description and a batch of resumes, processes each resume one by one, and evaluates how well each candidate matches the role. It safely handles missing or broken resumes, scores every candidate, and finally returns a ranked list of the best matches. The code is designed to be clean, reliable, and easy to extend."""

def process_batch(jd_text, resume_files):
    if not jd_text:
        raise ValueError("JD text missing")

    if not resume_files:
        raise ValueError("No resumes received in batch processor")

    results = []

    for resume in resume_files:
        parsed = parse_resume(resume)

        if "raw_text" not in parsed or "structured" not in parsed:
            continue  # skip broken resume safely

        screening = screen_candidate(jd_text, parsed["raw_text"])

        results.append({
            "candidate": parsed["structured"],
            "score": screening["score"],
            "decision": screening["decision"]
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# Why do you need batch_processor when screening_agent exists?

# screening_agent.py is designed to: Take one JD text,Take one resume text,Return a score + decision 

#batch_processor.py handles a list of resume files
# It: Loops through resumes , Calls parse_resume() , Calls screen_candidate() , Collects results ,Sorts candidates by score . It basically says: “Take all resumes and process them safely in bulk.”