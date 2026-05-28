import csv
import requests
from fuzzywuzzy import fuzz

SUI_RPC = "https://fullnode.mainnet.sui.io:443"


def get_object(obj_id, show_content=True, show_owner=False):
    """Fetch object data from Sui RPC."""
    options = {"showContent": show_content, "showOwner": show_owner}
    resp = requests.post(SUI_RPC, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "sui_getObject",
        "params": [obj_id, options]
    }, timeout=15)
    data = resp.json()
    if "error" in data or "error" in data.get("result", {}):
        return None
    return data.get("result", {}).get("data")


def check_object_valid(obj_id):
    """Check if the object ID exists on-chain as a moveObject. Returns fields or None."""
    data = get_object(obj_id)
    content = data.get("content") if data else None
    if content and content.get("dataType") == "moveObject":
        return content.get("fields")
    return None


def check_package_valid(package_id):
    """Check if the package ID exists on-chain as a valid package. Returns True/False."""
    data = get_object(package_id)
    content = data.get("content") if data else None
    return content is not None and content.get("dataType") == "package"


def check_wallet_owns_object(wallet_address, obj_id):
    """Check if the wallet address is the owner of the given object. Returns True/False."""
    data = get_object(obj_id, show_content=False, show_owner=True)
    if data is None:
        return None
    owner = data.get("owner", {}).get("AddressOwner", "")
    return owner.lower() == wallet_address.lower()


def check_deepsurge_valid(url):
    """Check if the URL is a valid DeepSurge link and returns a valid page. Returns True/False."""
    if "deepsurge.xyz" not in url.lower():
        return False
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        return resp.status_code == 200 and "404" not in resp.text[:500]
    except Exception:
        return False


def check_vercel_valid(url):
    """Check if the URL is a valid Vercel link and returns 200. Returns True/False."""
    if "vercel.app" not in url.lower():
        return False
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


def check_name_match(csv_name, onchain_name, ratio_threshold=70, partial_threshold=80):
    """Fuzzy compare csv_name vs onchain_name. Returns (is_match, ratio, partial_ratio)."""
    ratio = fuzz.ratio(csv_name.lower(), onchain_name.lower())
    partial = fuzz.partial_ratio(csv_name.lower(), onchain_name.lower())
    is_match = ratio >= ratio_threshold or partial >= partial_threshold
    return is_match, ratio, partial


def check_github_repo_name(github_url, last_name, ratio_threshold=70):
    """Check if the repo name's last segment (after last '_') fuzzy matches the last name."""
    url = github_url.strip().rstrip("#").removesuffix(".git")
    repo_name = url.rstrip("/").split("/")[-1]
    suffix = repo_name.rsplit("_", 1)[-1] if "_" in repo_name else repo_name
    ratio = fuzz.ratio(suffix.lower(), last_name.replace(" ", "").replace(".", "").lower())
    partial = fuzz.partial_ratio(suffix.lower(), last_name.replace(" ", "").replace(".", "").lower())
    is_match = ratio >= ratio_threshold or partial >= ratio_threshold
    return is_match, suffix, ratio, partial


rows = []

with open("test.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames + ["Valid", "Remarks"]
    for row in reader:
        obj_id = row["Published Object ID"].strip()
        package_id = row["Package ID"].strip()
        csv_name = f"{row['First name'].strip()} {row['Last name'].strip()}"
        remarks = []

        # Validate Package ID
        if not package_id:
            remarks.append("No Package ID")
        elif not check_package_valid(package_id):
            remarks.append("Invalid Package ID")

        # Validate Published Object ID
        if not obj_id:
            remarks.append("No Object ID")
        else:
            fields = check_object_valid(obj_id)
            if fields is None:
                remarks.append("Invalid Object ID")
            else:
                # Validate wallet owns the published object
                wallet = row["Active Sui wallet address"].strip()
                if not wallet:
                    remarks.append("No wallet address")
                else:
                    owns = check_wallet_owns_object(wallet, obj_id)
                    if owns is None:
                        remarks.append("Could not verify wallet ownership")
                    elif not owns:
                        remarks.append("Wallet does not own the object")

                # Validate name match
                onchain_name = fields.get("name")
                if not onchain_name:
                    remarks.append("Object has no name field")
                else:
                    is_match, ratio, partial = check_name_match(csv_name, onchain_name)
                    if not is_match:
                        remarks.append(f"Name mismatch (CSV: '{csv_name}' vs On-chain: '{onchain_name}')")

        # Validate Vercel URL
        vercel_url = row["Live Portfolio Vercel URL"].strip()
        if not vercel_url or vercel_url.lower() in ("n/a", "na"):
            remarks.append("No Vercel URL")
        elif not check_vercel_valid(vercel_url):
            remarks.append("Invalid Vercel URL (not vercel.app or unreachable)")

        # Validate DeepSurge profile link
        deepsurge_url = row["DeepSurge project link"].strip()
        if not deepsurge_url or deepsurge_url.lower() in ("n/a", "na"):
            remarks.append("No DeepSurge URL")
        elif not check_deepsurge_valid(deepsurge_url):
            remarks.append("Invalid DeepSurge URL (not deepsurge.xyz or unreachable)")

        # Validate GitHub repository link
        github_url = row["GitHub repository link"].strip()
        if not github_url:
            remarks.append("No GitHub URL")
        else:
            last_name = row["Last name"].strip()
            is_match, suffix, ratio, partial = check_github_repo_name(github_url, last_name)
            if not is_match:
                remarks.append(f"GitHub repo name mismatch ('{suffix}' vs '{last_name}')")

        valid = len(remarks) == 0
        row["Valid"] = valid
        row["Remarks"] = "; ".join(remarks) if remarks else ""
        rows.append(row)
        print(f"{'✓' if valid else '✗'} {csv_name} - {row['Remarks'] or 'All checks passed'}")

# Write results CSV
with open("results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nResults written to results.csv ({len(rows)} rows)")
