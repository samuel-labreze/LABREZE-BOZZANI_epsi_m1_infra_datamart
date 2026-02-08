import requests
import os
import json
import time

CLIENT_ID = os.getenv("WCL_CLIENT_ID", "a0e1dd3c-11ef-4fb4-8c64-2c7038b36c80")
CLIENT_SECRET = os.getenv("WCL_CLIENT_SECRET", "iFxS1AHSOUu5G4GeSwBcmMFqBOUez61xPKyUCMdl")

def get_token():
    response = requests.post(
        "https://www.warcraftlogs.com/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    if response.status_code != 200:
        print(f"Error getting token: {response.text}")
        return None
    return response.json()["access_token"]

def check_rate_limit():
    token = get_token()
    if not token:
        return

    # On fait une requête très légère pour récupérer les headers de rate limit
    query = "{ rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn } }"
    
    response = requests.post(
        "https://www.warcraftlogs.com/api/v2/client",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json().get("data", {}).get("rateLimitData", {})
        limit = data.get("limitPerHour", 0)
        spent = data.get("pointsSpentThisHour", 0)
        reset = data.get("pointsResetIn", 0)
        
        remaining = limit - spent
        percent_used = (spent / limit) * 100 if limit > 0 else 0
        reset_minutes = reset // 60
        
        print("\n=== WarcraftLogs API Rate Limit Status ===")
        print(f"Points Used:      {spent} / {limit} ({percent_used:.1f}%)")
        print(f"Points Remaining: {remaining}")
        print(f"Reset In:         {reset_minutes} minutes")
        print("==========================================\n")
    else:
        print(f"API Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_rate_limit()
