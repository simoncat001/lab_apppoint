import requests

def test_login_response():
    url = "http://127.0.0.1:8000/api/auth/login/json"
    payload = {
        "username": "admin",
        "password": "admin_password_123"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response keys:", data.keys())
            if "user" in data:
                print("User data found:", data["user"])
            else:
                print("ERROR: 'user' key missing in response!")
                
            if "access_token" in data:
                print("Access token found.")
        else:
            print("Login failed:", response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_login_response()
