import requests
import json

TOKEN = "???"
HEADERS = {"Authorization": f"token {TOKEN}"}

def get_repos():
    url = "https://api.github.com/user/repos?per_page=200"
    return requests.get(url, headers=HEADERS).json()

def compress_views(data):
    count = data.get("count", 0)
    uniques = data.get("uniques", 0)
    if count == 0 and uniques == 0:
        return None
    return f"{count}u{uniques}"

def compress_clones(data):
    count = data.get("count", 0)
    uniques = data.get("uniques", 0)
    if count == 0 and uniques == 0:
        return None
    return f"{count}u{uniques}"

def compress_referrers(refs):
    if not refs:
        return None
    out = {}
    for r in refs:
        out[r["referrer"]] = f"{r['count']}u{r['uniques']}"
    return out

def compress_paths(paths):
    if not paths:
        return None
    out = {}
    for p in paths:
        out[p["title"]] = f"{p['count']}u{p['uniques']}"
    return out

def get_traffic(repo_full_name):
    base = f"https://api.github.com/repos/{repo_full_name}/traffic"
    views = requests.get(f"{base}/views", headers=HEADERS).json()
    clones = requests.get(f"{base}/clones", headers=HEADERS).json()
    referrers = requests.get(f"{base}/popular/referrers", headers=HEADERS).json()
    paths = requests.get(f"{base}/popular/paths", headers=HEADERS).json()

    compact = {}

    cv = compress_views(views)
    if cv:
        compact["views"] = cv

    cc = compress_clones(clones)
    if cc:
        compact["clones"] = cc

    cr = compress_referrers(referrers)
    if cr:
        compact["referrers"] = cr

    cp = compress_paths(paths)
    if cp:
        compact["paths"] = cp

    return compact

def main():
    repos = get_repos()
    output = {}

    for repo in repos:
        name = repo["full_name"]
        print(f"Fetching: {name}")
        compact = get_traffic(name)
        if compact:  # only include repos with non-zero activity
            output[name] = compact

    with open("github_traffic_compact.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\nSaved to github_traffic_compact.json")

if __name__ == "__main__":
    main()
