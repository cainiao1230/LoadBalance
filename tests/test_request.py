import json
import requests


def main() -> None:
    url = "http://192.0.2.1:8000/api/task/quick-submit"
    #url = "http://localhost:8000/api/task/quick-submit"
    encrypted_data = "1a339b74f3940fbe1276cdca15cb2db9288f60e4898d7745f499985c1ead0fe792bf8230248634abd6051aebe8a896dfa15639ae4d8af70e60842197f8caeb97aba84c13e63e676dd6075ec42771f83dcb9985332cfa7838f236978b7bc5c3a96f3f9fb8e993ca3d6ee3b8ee876f5aa286826a9a87e4626d4771df04c4b0e7c9701a497f709ce4c6a644a7921a5731cb9d367281f24fd536316fbb5a3aab884ace3c548572829188cd5515740ba6c079"
    
    params = {
        "username": "ceshi2",
        "password": "123456",
        "encrypted_data": encrypted_data
    }
    resp = requests.get(url, params=params, timeout=60)
    try:
        body = resp.json()
    except Exception:
        body = None

    print("HTTP:", resp.status_code)
    if body:

        print(body)
    else:
        print(resp.text)

    # 新账号请求
    params2 = {
        "username": "ceshi1",  # 替换为你数据库中存在的另一个账号
        "password": "123456",    # 替换为该账号的密码
        "encrypted_data": encrypted_data,
    }
    resp2 = requests.get(url, params=params2, timeout=60)
    try:
        body2 = resp2.json()
    except Exception:
        body2 = None

    print("\n--- 另一个账号请求响应 ---")
    print("HTTP:", resp2.status_code)
    if body2:
        print(body2)
    else:
        print(resp2.text)


if __name__ == "__main__":
    main()
