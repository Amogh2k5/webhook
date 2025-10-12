import requests
from fastapi import FastAPI, HTTPException
from datetime import datetime
import google.generativeai as genai

app = FastAPI()

# GitHub repo info
GITHUB_TOKEN = "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"
REPO_FULL_NAME = "Amogh2k5/webhook"
BRANCH = "main"

# Gemini model for meaningful commit check
GENIE_MODEL_NAME = "gemini-2.0-flash"
genai.configure(api_key="AIzaSyCyAf0B1uWmngRjDVeE-HmqAPqgLivrSG8")

# Global variables to store code strings
old_code = ""
new_code = ""


def is_meaningful_change(old_code: str, new_code: str) -> bool:
    """
    Sends old and new code to Gemini to check how meaningful the changes are.
    Returns an integer 0-100 indicating the degree of meaningful change.
    """

    # Fast path: if exactly same, return 0
    if old_code.strip() == new_code.strip():
        return 0
    
    system_prompt = (
        "You are an expert Python developer and code reviewer.\n"
        "Compare the two code versions provided.\n"
        "Determine how meaningful the changes are (functional, logical, bug fixes, performance improvements).\n"
        "Ignore purely cosmetic changes like whitespace, comments, or formatting.\n"
        "Return ONLY a numeric score from 0 (no meaningful change) to 100 (very meaningful change).\n"
    )

    user_prompt = f"""
OLD CODE:
{old_code}

NEW CODE:
{new_code}

Answer with a number from 0 to 100:
"""

    combined_prompt = system_prompt + "\n" + user_prompt

    model = genai.GenerativeModel(GENIE_MODEL_NAME)
    response = model.generate_content(
        combined_prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="text/plain"
        )
    )

    try:
        score = int(response.text.strip())
        return max(0, min(score, 100))  # clamp to 0–100
    except:
        return 0  # fallback

@app.get("/check_latest_commit")
def process_latest_commit():
    """
    Fetch the latest commit from GitHub, get old and new code as-is, and check if changes are meaningful.
    """
    global old_code, new_code
    try:
        # Step 1: Get latest commit
        commits_url = f"https://api.github.com/repos/{REPO_FULL_NAME}/commits?sha={BRANCH}&per_page=1"
        res = requests.get(commits_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail="Failed to fetch commits")

        latest_commit = res.json()[0]
        latest_sha = latest_commit["sha"]

        # Step 2: Get commit details (changed files)
        commit_url = f"https://api.github.com/repos/{REPO_FULL_NAME}/commits/{latest_sha}"
        res_commit = requests.get(commit_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if res_commit.status_code != 200:
            raise HTTPException(status_code=res_commit.status_code, detail="Failed to fetch commit details")

        files = res_commit.json().get("files", [])
        if not files:
            return {"status": "success", "message": "No changed files in latest commit"}

        # Step 3: For simplicity, just take the first changed file
        file_path = files[0]["filename"]

        # Step 4: Fetch old code from previous commit
        parent_sha = latest_commit["parents"][0]["sha"]
        raw_url_old = f"https://raw.githubusercontent.com/{REPO_FULL_NAME}/{parent_sha}/{file_path}"
        res_old = requests.get(raw_url_old, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        old_code = res_old.text if res_old.status_code == 200 else ""

        # Step 5: Fetch new code from latest commit
        raw_url_new = f"https://raw.githubusercontent.com/{REPO_FULL_NAME}/{latest_sha}/{file_path}"
        res_new = requests.get(raw_url_new, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if res_new.status_code != 200:
            raise HTTPException(status_code=res_new.status_code, detail=f"Failed to fetch latest file: {file_path}")
        new_code = res_new.text

        # Step 6: Check if the commit is meaningful
        meaningful = is_meaningful_change(old_code, new_code)

        return {
            "status": "success",
            "file": file_path,
            "meaningful_change": meaningful,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/last_code")
def get_last_code():
    """
    Retrieve last old and new code strings
    """
    if not old_code or not new_code:
        return {"message": "No code processed yet"}
    return {"old_code": old_code, "new_code": new_code}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("compare_code:app", host="127.0.0.1", port=8001, reload=True)

