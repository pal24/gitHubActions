import requests
import csv
from datetime import datetime

# ==== Configuration ====
GITHUB_TOKEN = "uyegegdydgebd"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

REPOS = [
    "pal24/gitHubActions",
    "pal24/gitHubAction",
    # Add more repositories as needed
]

WORKFLOW_FILE_NAME = "deploy-uat.yml"
BRANCH = "main"
OUTPUT_CSV = "deploy_uat_metadata.csv"

# ==== Functions ====

def get_workflow_id(repo):
    """Fetch workflow ID by file name."""
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    workflows = response.json()["workflows"]
    for wf in workflows:
        if wf["path"].endswith(WORKFLOW_FILE_NAME):
            return wf["id"]
    return None

def get_workflow_runs(repo, workflow_id):
    """Get workflow runs for a specific workflow ID and branch."""
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs?branch={BRANCH}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("workflow_runs", [])

def get_artifacts(repo, run_id):
    """Get artifact names for a specific workflow run."""
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    artifacts = response.json().get("artifacts", [])
    return [artifact["name"] for artifact in artifacts]

# ==== Main Logic ====

results = []

for repo in REPOS:
    print(f"Processing repo: {repo}")
    try:
        workflow_id = get_workflow_id(repo)
        if not workflow_id:
            print(f"Workflow {WORKFLOW_FILE_NAME} not found in {repo}")
            continue

        runs = get_workflow_runs(repo, workflow_id)
        for run in runs:
            metadata = {
                "repository": repo,
                "status": run["status"],
                "conclusion": run["conclusion"],
                "commit": run["head_sha"],
                "timestamp": run["created_at"],
                "user": run["triggering_actor"]["login"],
                "artifacts": ", ".join(get_artifacts(repo, run["id"]))
            }
            results.append(metadata)
    except Exception as e:
        print(f"Error processing {repo}: {e}")

# ==== Write to CSV ====

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["repository", "status", "conclusion", "commit", "timestamp", "user", "artifacts"])
    writer.writeheader()
    writer.writerows(results)

print(f"\n✅ Metadata exported to {OUTPUT_CSV}")
