import requests
import csv
from datetime import datetime, timedelta

# GitHub Token (keep it secure!)
GITHUB_TOKEN = "ghp_your_token_here"  # <-- Replace with your token
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# List your repositories here
REPOS = [
    "org1/repo1",
    "org2/repo2",
    # Add more repos as needed
]

WORKFLOW_FILENAME = "deploy.yml"
BRANCH = "main"
DAYS = 15
CSV_FILE = "workflow_deploy_metadata.csv"

def get_workflow_id(repo):
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    workflows = r.json().get("workflows", [])
    for wf in workflows:
        if wf["path"].endswith(WORKFLOW_FILENAME):
            return wf["id"]
    return None

def get_recent_runs(repo, workflow_id):
    since = (datetime.utcnow() - timedelta(days=DAYS)).isoformat() + "Z"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs"
    params = {
        "branch": BRANCH,
        "per_page": 50,
    }
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    all_runs = r.json().get("workflow_runs", [])
    recent_runs = [run for run in all_runs if run["created_at"] >= since]
    return recent_runs

def extract_run_metadata(repo, run):
    return {
        "repository": repo,
        "status": run.get("status"),
        "timestamp": run.get("created_at"),
        "conclusion": run.get("conclusion"),
        "commit_message": run["head_commit"]["message"] if run.get("head_commit") else "N/A",
        "triggered_by": run.get("triggering_actor", {}).get("login", "N/A"),
    }

def main():
    all_data = []

    for repo in REPOS:
        print(f"Processing: {repo}")
        try:
            wf_id = get_workflow_id(repo)
            if not wf_id:
                print(f"  No deploy.yml workflow found.")
                all_data.append({
                    "repository": repo,
                    "status": "NO RUN",
                    "timestamp": "",
                    "conclusion": "",
                    "commit_message": "",
                    "triggered_by": ""
                })
                continue

            runs = get_recent_runs(repo, wf_id)
            if not runs:
                all_data.append({
                    "repository": repo,
                    "status": "NO RUN",
                    "timestamp": "",
                    "conclusion": "",
                    "commit_message": "",
                    "triggered_by": ""
                })
            else:
                for run in runs:
                    metadata = extract_run_metadata(repo, run)
                    all_data.append(metadata)

        except Exception as e:
            print(f"  Error processing {repo}: {e}")
            all_data.append({
                "repository": repo,
                "status": "ERROR",
                "timestamp": "",
                "conclusion": "",
                "commit_message": str(e),
                "triggered_by": ""
            })

    # Write to CSV
    with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "repository", "status", "timestamp", "conclusion", "commit_message", "triggered_by"
        ])
        writer.writeheader()
        for row in all_data:
            writer.writerow(row)

    print(f"\n✅ Metadata written to: {CSV_FILE}")

if __name__ == "__main__":
    main()
