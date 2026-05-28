import csv
import requests
from fuzzywuzzy import fuzz

SUI_RPC = "https://fullnode.mainnet.sui.io:443"


def check_object_valid(obj_id):
    """Check if the object ID exists on-chain. Returns the object fields or None."""
    resp = requests.post(SUI_RPC, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "sui_getObject",
        "params": [obj_id, {"showContent": True}]
    }, timeout=15)
    data = resp.json()
    if "error" in data or "error" in data.get("result", {}):
        return None
    return data.get("result", {}).get("data", {}).get("content", {}).get("fields")


def check_name_match(csv_name, onchain_name, ratio_threshold=70, partial_threshold=80):
    """Fuzzy compare csv_name vs onchain_name. Returns (is_match, ratio, partial_ratio)."""
    ratio = fuzz.ratio(csv_name.lower(), onchain_name.lower())
    partial = fuzz.partial_ratio(csv_name.lower(), onchain_name.lower())
    is_match = ratio >= ratio_threshold or partial >= partial_threshold
    return is_match, ratio, partial


with open("test.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        obj_id = row["Published Object ID"].strip()
        csv_name = f"{row['First name'].strip()} {row['Last name'].strip()}"

        if not obj_id:
            print(f"[SKIP] {csv_name} - No Object ID")
            continue

        fields = check_object_valid(obj_id)
        if fields is None:
            print(f"[INVALID OBJECT] {csv_name} - Object ID not found: {obj_id}")
            continue

        onchain_name = fields.get("name")
        if not onchain_name:
            print(f"[NO NAME] {csv_name} - Object exists but has no name field")
            continue

        is_match, ratio, partial = check_name_match(csv_name, onchain_name)
        status = "MATCH" if is_match else "MISMATCH"
        print(f"[{status}] CSV: '{csv_name}' | On-chain: '{onchain_name}' | ratio={ratio} partial={partial}")
