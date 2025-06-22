import re
import csv
import time
import requests
from tenacity import retry, wait_exponential, stop_after_attempt

# ---- Configuration ----
GITHUB_TOKEN = 'your_github_token_here'
ORG = 'your_org_name_here'
WORKFLOW_REGEX = r"deploy.*uat.*\.ya?ml"
BRANCH = 'main'
CSV_FILE = 'github_deployment_metadata.csv'

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

@retry(wait=wait_exponential(multiplier=2, min=5, max=60), stop=stop_after_attempt(5))
def github_get(url, params=None):
    """Performs GitHub API GET with retry and rate-limit handling"""
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
        reset_time = int(response.headers["X-RateLimit-Reset"])
        wait_time = reset_time - int(time.time()) + 5
        print(f"[Rate Limit Hit] Sleeping for {wait_time}s...")
        time.sleep(max(wait_time, 0))
        raise Exception("Retrying after rate limit reset")
    response.raise_for_status()
    return response.json()

def get_all_repos():
    """Fetch all repositories in the org/user"""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos"
        params = {"per_page": 100, "page": page}
        page_data = github_get(url, params)
        if not page_data:
            break
        repos.extend(page_data)
        page += 1
    return repos

def get_workflows(repo):
    """List workflows in a given repo"""
    url = f"https://api.github.com/repos/{ORG}/{repo}/actions/workflows"
    data = github_get(url)
    return data.get("workflows", [])

def get_latest_run(repo, workflow_id):
    """Fetch the latest workflow run on the main branch"""
    url = f"https://api.github.com/repos/{ORG}/{repo}/actions/workflows/{workflow_id}/runs"
    params = {"branch": BRANCH, "per_page": 1}
    data = github_get(url, params)
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None

def extract_metadata(repo, workflow, run):
    """Extracts required metadata for the dashboard"""
    return {
        "repo": repo,
        "workflow_name": workflow.get("name", ""),
        "description": run.get("display_title", ""),
        "status": run.get("status", ""),
        "conclusion": run.get("conclusion", ""),
        "commit_id": run.get("head_sha", ""),
        "timestamp": run.get("created_at", ""),
        "html_url": run.get("html_url", "")
    }

def main():
    print("Fetching repositories...")
    repos = get_all_repos()
    print(f"Found {len(repos)} repositories.")

    all_data = []

    for repo in repos:
        repo_name = repo["name"]
        print(f"Checking repo: {repo_name}")
        try:
            workflows = get_workflows(repo_name)
            for wf in workflows:
                wf_filename = wf.get("path", "")
                if re.search(WORKFLOW_REGEX, wf_filename, re.IGNORECASE):
                    run = get_latest_run(repo_name, wf["id"])
                    if run and run.get("head_branch") == BRANCH:
                        data = extract_metadata(repo_name, wf, run)
                        all_data.append(data)
        except Exception as e:
            print(f"Error processing repo {repo_name}: {e}")
            continue

    print(f"Writing {len(all_data)} records to CSV...")
    with open(CSV_FILE, "w", newline='') as csvfile:
        fieldnames = ["repo", "workflow_name", "description", "status", "conclusion", "commit_id", "timestamp", "html_url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)

    print(f"✅ Done. Data written to {CSV_FILE}")

if __name__ == "__main__":
    main()
