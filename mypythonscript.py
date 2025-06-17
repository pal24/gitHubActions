import requests
import csv

# ==== CONFIGURATION ====
GITHUB_TOKEN = 'tetxgydd'
REPOS = [  # Format: ("owner", "repo")
    ("octocat", "Hello-World"),
    ("pal24", "gitHubActions"),
    # Add more as needed
]
BRANCH = "main"
CSV_FILENAME = "workflow_runs_metadata.csv"
MAX_RUNS_PER_REPO = 10  # Change as needed
# ========================

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def get_workflow_runs(owner, repo, branch="main", per_page=10):
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    params = {
        "branch": branch,
        "per_page": per_page
    }

    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch for {owner}/{repo}: {response.status_code}")
        return []

    return response.json().get('workflow_runs', [])

def collect_data():
    all_data = []

    for owner, repo in REPOS:
        print(f"Fetching workflow runs for {owner}/{repo} on branch '{BRANCH}'...")
        runs = get_workflow_runs(owner, repo, BRANCH, MAX_RUNS_PER_REPO)
        for run in runs:
            all_data.append({
                "owner": owner,
                "repository": repo,
                "workflow_name": run.get("name"),
                "run_id": run.get("id"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "run_started_at": run.get("run_started_at"),
                "html_url": run.get("html_url"),
                "branch": run.get("head_branch"),
                "commit_message": run.get("head_commit", {}).get("message"),
                "commit_sha": run.get("head_sha"),
            })
    return all_data

def export_to_csv(data, filename):
    if not data:
        print("No data to export.")
        return

    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    print(f"✅ Exported {len(data)} workflow runs to {filename}")

if __name__ == "__main__":
    all_runs = collect_data()
    export_to_csv(all_runs, CSV_FILENAME)
