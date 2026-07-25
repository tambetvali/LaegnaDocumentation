import requests
import json

TOKEN = "???"
HEADERS = {"Authorization": f"token {TOKEN}"}

def get_repos():
    url = "https://api.github.com/user/repos?per_page=200"
    return requests.get(url, headers=HEADERS).json()

def get_traffic(repo_full_name):
    base = f"https://api.github.com/repos/{repo_full_name}/traffic"
    return {
        "views": requests.get(f"{base}/views", headers=HEADERS).json(),
        "clones": requests.get(f"{base}/clones", headers=HEADERS).json(),
        "referrers": requests.get(f"{base}/popular/referrers", headers=HEADERS).json(),
        "paths": requests.get(f"{base}/popular/paths", headers=HEADERS).json()
    }

def main():
    repos = get_repos()
    output = {}

    for repo in repos:
        name = repo["full_name"]
        print(f"Fetching: {name}")
        output[name] = get_traffic(name)

    with open("github_traffic_2weeks.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nSaved to github_traffic_2weeks.json")

if __name__ == "__main__":
    main()
