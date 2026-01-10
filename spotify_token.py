import requests
import base64

CLIENT_ID = "c96951bf51d74a4b87ceb1f7dc6a0fea"
CLIENT_SECRET = "1ebde6feea114d2ca5512c5af5eae6b0"

def get_spotify_token():
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    res = requests.post("https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {b64_auth}"},
        data={"grant_type": "client_credentials"}
    )

    data = res.json()
    print("Spotify 回應:", data)  # Debug 用

    if "access_token" not in data:
        raise Exception(f"Spotify Token 取得失敗: {data}")

    return data["access_token"]
if __name__ == "__main__":
    token = get_spotify_token()
    print("取得的 Spotify Token:", token)