import requests
import json
import os
from collections import Counter
from statistics import mean, median, multimode, pstdev, pvariance, stdev, variance

TOKEN = "???"
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def get_json(url, expected_type):
    response = requests.get(url, headers=HEADERS, timeout=30)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            data = response.json()
        except ValueError:
            data = None
        message = data.get("message", str(exc)) if isinstance(data, dict) else str(exc)
        raise RuntimeError(f"GitHub API request failed for {url}: {message}") from exc

    data = response.json()
    if not isinstance(data, expected_type):
        message = data.get("message", "unexpected response") if isinstance(data, dict) else "unexpected response"
        raise RuntimeError(f"Unexpected GitHub API response from {url}: {message}")
    return data

def get_repos():
    if not TOKEN:
        raise RuntimeError("Set GITHUB_TOKEN or GH_TOKEN to a GitHub token with repository access.")

    url = "https://api.github.com/user/repos?per_page=200"
    return get_json(url, list)

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

def compress_daily(data):
    return [f"{day['count']}u{day['uniques']}" for day in data]

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
    views = get_json(f"{base}/views", dict)
    clones = get_json(f"{base}/clones", dict)
    referrers = get_json(f"{base}/popular/referrers", list)
    paths = get_json(f"{base}/popular/paths", list)

    compact = {}

    cv = compress_views(views)
    if cv:
        compact["views"] = cv

    cc = compress_clones(clones)
    if cc:
        compact["clones"] = cc

    if cv:
        compact["dailyviews"] = compress_daily(views.get("views", []))
    if cc:
        compact["dailyclones"] = compress_daily(clones.get("clones", []))

    cr = compress_referrers(referrers)
    if cr:
        compact["referrers"] = cr

    cp = compress_paths(paths)
    if cp:
        compact["paths"] = cp

    return compact

def parse_compact(value):
    count, unique = value.split("u", 1)
    return int(count), int(unique)

def summarize_numbers(values):
    ordered = sorted(values)
    size = len(ordered)
    if not size:
        return {"n": 0}

    if size == 1:
        q1 = q3 = ordered[0]
    else:
        midpoint = size // 2
        lower_half = ordered[:midpoint]
        upper_half = ordered[(size + 1) // 2:]
        q1 = median(lower_half)
        q3 = median(upper_half)

    frequencies = Counter(ordered)
    modes = multimode(ordered) if max(frequencies.values()) > 1 else []
    average = mean(ordered)
    population_stddev = pstdev(ordered)
    standardized = [(value - average) / population_stddev for value in ordered] if population_stddev else None
    result = {
        "n": size,
        "total": sum(ordered),
        "mean": average,
        "median": median(ordered),
        "mode": modes,
        "min": ordered[0],
        "max": ordered[-1],
        "range": ordered[-1] - ordered[0],
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "sum_squares": sum(value * value for value in ordered),
        "mean_absolute_deviation": mean(abs(value - average) for value in ordered),
        "population_variance": pvariance(ordered),
        "population_stddev": population_stddev,
        "sample_variance": variance(ordered) if size > 1 else None,
        "sample_stddev": stdev(ordered) if size > 1 else None,
        "standard_error": stdev(ordered) / size ** 0.5 if size > 1 else None,
        "coefficient_of_variation": population_stddev / abs(average) if average else None,
        "skewness": mean(value ** 3 for value in standardized) if standardized else None,
        "excess_kurtosis": mean(value ** 4 for value in standardized) - 3 if standardized else None,
    }
    return result

def summarize_traffic(repositories):
    observations = {"views": [], "clones": [], "referrers": [], "paths": []}
    for traffic in repositories.values():
        for metric in ("views", "clones"):
            if metric in traffic:
                observations[metric].append(parse_compact(traffic[metric]))
        for breakdown in ("referrers", "paths"):
            for value in traffic.get(breakdown, {}).values():
                observations[breakdown].append(parse_compact(value))

    return {
        category: {
            "count": summarize_numbers([pair[0] for pair in pairs]),
            "unique": summarize_numbers([pair[1] for pair in pairs]),
        }
        for category, pairs in observations.items()
        if pairs
    }

def main():
    repos = get_repos()
    output = {}

    for repo in repos:
        name = repo["full_name"]
        print(f"Fetching: {name}")
        compact = get_traffic(name)
        if compact:  # only include repos with non-zero activity
            output[name] = compact

    result = {
        "_documentation": {
            "format": "Traffic values use '<count>u<unique>'; for example, '1u1' means 1 total event and 1 unique visitor or cloner. dailyviews and dailyclones are arrays of these values in the order returned by GitHub, with up to 14 daily entries.",
            "scope": "GitHub traffic API values cover its rolling 14-day reporting window.",
            "unique_counts": "Unique counts are reported independently for each repository or breakdown; summing them does not deduplicate people across entries.",
            "breakdowns": "Referrers and paths contain only the popular entries returned by GitHub, so their totals are partial rather than repository-wide totals.",
            "statistics": "Statistics summarize each reported repository metric or returned referrer/path entry. Quartiles use the median-of-halves method; sample variance and standard deviation are null when fewer than two observations exist. Modes are empty when no value repeats.",
        },
        "_statistics": summarize_traffic(output),
    }
    result.update(output)

    with open("github_traffic_compact.json", "w") as f:
        json.dump(result, f, indent=2)

    print("\nSaved to github_traffic_compact.json")

if __name__ == "__main__":
    main()
