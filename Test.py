import requests
import pandas as pd
import time
import re
from datetime import datetime

# ----------------- CONFIG -----------------
GITHUB_TOKEN = 'ghp_XXXXXXXXXXXXXXXXXXXXXX'
ORG_NAME = 'your-org-name'
WORKFLOW_REGEX = r"deploy.*uat.*\.ya?ml"  # handles .yml or .yaml
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'}
BASE_API = 'https://api.github.com'
RATE_LIMIT_THRESHOLD = 100
OUTPUT_CSV = 'deployment_metadata.csv'

# ----------- PAGINATION HANDLER -----------
def paginated_get(url):
    results = []
    while url:
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 403:
            reset_time = int(r.headers.get("X-RateLimit-Reset", time.time() + 60))
            sleep_for = reset_time - time.time() + 5
            print(f"Rate limit hit. Sleeping for {sleep_for:.0f} seconds.")
            time.sleep(max(sleep_for, 0))
            continue
        r.raise_for_status()
        results.extend(r.json())
        url = r.links.get('next', {}).get('url')
    return results

# ----------- GET WORKFLOW METADATA -----------
def get_repo_workflows(repo):
    url = f"{BASE_API}/repos/{ORG_NAME}/{repo}/actions/workflows"
    return paginated_get(url)

def get_workflow_runs(repo, workflow_id):
    url = f"{BASE_API}/repos/{ORG_NAME}/{repo}/actions/workflows/{workflow_id}/runs?branch=main"
    return paginated_get(url)

def get_release_tag(repo, commit_sha):
    url = f"{BASE_API}/repos/{ORG_NAME}/{repo}/tags"
    tags = paginated_get(url)
    for tag in tags:
        if tag['commit']['sha'] == commit_sha:
            return tag['name']
    return None

# ----------- MAIN FUNCTION -----------
def collect_metadata():
    print("Fetching repositories...")
    repos = paginated_get(f"{BASE_API}/orgs/{ORG_NAME}/repos?per_page=100")

    all_data = []
    for repo in repos:
        repo_name = repo['name']
        print(f"Checking repo: {repo_name}")
        try:
            workflows = get_repo_workflows(repo_name)
            for wf in workflows:
                wf_name = wf['name']
                if re.match(WORKFLOW_REGEX, wf['path'], re.IGNORECASE):
                    runs = get_workflow_runs(repo_name, wf['id'])
                    for run in runs:
                        if run['head_branch'] != 'main':
                            continue
                        commit_sha = run['head_sha']
                        release_tag = get_release_tag(repo_name, commit_sha)
                        all_data.append({
                            "repository": repo_name,
                            "workflow": wf_name,
                            "description": run.get('display_title', ''),
                            "status": run['status'],
                            "conclusion": run['conclusion'],
                            "commit_id": commit_sha,
                            "html_url": run['html_url'],
                            "timestamp": run['run_started_at'],
                            "release_tag": release_tag
                        })
        except Exception as e:
            print(f"Error processing repo {repo_name}: {e}")

    df = pd.DataFrame(all_data)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    collect_metadata()
