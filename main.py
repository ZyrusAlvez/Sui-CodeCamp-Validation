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
        package_id = row["Package ID"].strip()
        csv_name = f"{row['First name'].strip()} {row['Last name'].strip()}"

        # Validate Package ID
        if not package_id:
            print(f"[SKIP PACKAGE] {csv_name} - No Package ID")
        elif check_package_valid(package_id):
            print(f"[VALID PACKAGE] {csv_name} - {package_id}")
        else:
            print(f"[INVALID PACKAGE] {csv_name} - {package_id}")

        # Validate Published Object ID and name
        if not obj_id:
            print(f"[SKIP OBJECT] {csv_name} - No Object ID")
            continue

        fields = check_object_valid(obj_id)
        if fields is None:
            print(f"[INVALID OBJECT] {csv_name} - {obj_id}")
            continue

        # Validate wallet owns the published object
        wallet = row["Active Sui wallet address"].strip()
        if not wallet:
            print(f"[SKIP WALLET] {csv_name} - No wallet address")
        else:
            owns = check_wallet_owns_object(wallet, obj_id)
            if owns is None:
                print(f"[WALLET CHECK FAILED] {csv_name} - Could not verify ownership")
            elif owns:
                print(f"[WALLET MATCH] {csv_name} - Wallet owns the object")
            else:
                print(f"[WALLET MISMATCH] {csv_name} - Wallet does NOT own the object")

        onchain_name = fields.get("name")
        if not onchain_name:
            print(f"[NO NAME] {csv_name} - Object exists but has no name field")
            continue

        is_match, ratio, partial = check_name_match(csv_name, onchain_name)
        status = "MATCH" if is_match else "MISMATCH"
        print(f"[{status}] CSV: '{csv_name}' | On-chain: '{onchain_name}' | ratio={ratio} partial={partial}")
