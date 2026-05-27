import csv
import requests
from fuzzywuzzy import fuzz

SUI_RPC = "https://fullnode.mainnet.sui.io:443"

def get_onchain_name(obj_id):
    resp = requests.post(SUI_RPC, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "sui_getObject",
        "params": [obj_id, {"showContent": True}]
    }, timeout=15)
    data = resp.json()
    fields = data.get("result", {}).get("data", {}).get("content", {}).get("fields", {})
    return fields.get("name")

with open("test.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        obj_id = row["Published Object ID"].strip()
        csv_name = f"{row['First name'].strip()} {row['Last name'].strip()}"

        if not obj_id:
            print(f"[SKIP] {csv_name} - No Object ID")
            continue

        try:
            onchain_name = get_onchain_name(obj_id)
            if onchain_name:
                ratio = fuzz.ratio(csv_name.lower(), onchain_name.lower())
                partial = fuzz.partial_ratio(csv_name.lower(), onchain_name.lower())
                status = "MATCH" if ratio >= 70 or partial >= 80 else "MISMATCH"
                print(f"[{status}] CSV: '{csv_name}' | On-chain: '{onchain_name}' | ratio={ratio} partial={partial}")
            else:
                print(f"[NOT FOUND] {csv_name} - No name field in object {obj_id}")
        except Exception as e:
            print(f"[ERROR] {csv_name} - {e}")
