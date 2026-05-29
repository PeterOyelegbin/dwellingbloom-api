from requests import request
from decouple import config
from .logger_config import general_logger

# Function to verify BVN
def youverify_kyc(data: dict):
    url = config('YOUVERIFY_API_URL')
    headers = {'Content-Type': 'application/json', 'token': config('YOUVERIFY_API_KEY')}
    payload = {
        "id": data["bvn"],
        "metadata": {
            "firstName": data["first_name"],
            "lastName": data["last_name"]
        },
        "isSubjectConsent": True,
        "shouldRetrivedNin": True
    }
    try:
        response = request("POST", url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        general_logger.error(f"YouVerify API error: {str(e)}")
        raise

def dojah_kyc(data: dict):
    url = config('DOJAH_API_URL')
    headers = {'Content-Type': 'application/json', 'AppId': config('DOJAH_APP_ID'), 'Authorization': config("DOJAH_API_KEY")}
    payload = {
        "bvn": data["bvn"],
        "first_name": data["first_name"],
        "last_name": data["last_name"]
    }
    try:
        response = request("GET", url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        general_logger.error(f"Dojah API error: {str(e)}")
        raise

def verify_bvn(user_data: dict) -> dict:
    try:
        main_verification = youverify_kyc(user_data)
        if main_verification.get("success") is False:
            general_logger.error("YouVerify verification failed, trying Dojah backup")
            raise Exception("YouVerify verification failed")
        matching_data = main_verification.get("data", {})
        if matching_data.get("firstName") == user_data["first_name"] and matching_data.get("lastName") == user_data["last_name"] and matching_data.get("nin") == user_data["nin"]:
            general_logger.info(f"{user_data['first_name']} {user_data['last_name']} is verified according to YouVerify")
            return {"success": True, "provider": "YouVerify"}
        else:
            general_logger.error(f"{user_data['first_name']} {user_data['last_name']} is not valid according to YouVerify")
            return {"success": False, "provider": "YouVerify"}
    except Exception:
        try:
            backup_verification = dojah_kyc(user_data)
            matching_data = backup_verification.get("entity", {})
            if  matching_data.get("first_name", {}).get("status") == "true" and matching_data.get("last_name", {}).get("status") == "true":
                general_logger.info(f"{user_data['first_name']} {user_data['last_name']} is verified according to Dojah")
                return {"success": True, "provider": "Dojah"}
            else:
                general_logger.error(f"{user_data['first_name']} {user_data['last_name']} is not valid according to Dojah")
                return {"success": False, "provider": "Dojah"}
        except Exception as e:
            general_logger.error(f"Verification failed: {str(e)}")
            raise Exception("Verification service is currently unavailable, please try again later.")
