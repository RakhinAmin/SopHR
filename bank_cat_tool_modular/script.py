import os
import json

path = ".secrets/credentials.json"
data = {"test": 1}

try:
    with open(path, "w") as f:
        json.dump(data, f)
    print("✅ File written successfully")
except Exception as e:
    print(f"❌ Failed to write: {e}")
