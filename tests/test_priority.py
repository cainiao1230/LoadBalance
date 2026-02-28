import json
import requests
import threading


def send_request(username, password, encrypted_data):
    """发送单个请求"""
    url = "http://192.0.2.1:8000/api/task/quick-submit"
    params = {
        "username": username,
        "password": password,
        "encrypted_data": encrypted_data,
    }
    resp = requests.get(url, params=params, timeout=60)
    try:
        body = resp.json()
    except Exception:
        body = None

    print(f"\n--- {username} 请求响应 ---")
    print("HTTP:", resp.status_code)
    if body:
        print(body)
    else:
        print(resp.text)


def main() -> None:
    encrypted_data = (
        "77e19b17f33dfabeba6fddca67e12d9a8ccd7be4e49a5645da1a000ccb683883ebf1633b188634abd605962bd1e24aa38fb2c9ae4d8a2a68607edf97f87c115cbba8705e7e4cee90d63c5eb07071c0c5cb9985332cfa9c2aabf2cdc135b640a9873770d6127dca376ef5949c878d1d2d863d5677408f10bb2ddadf04c4f6adc9706e2e36d9f9c9dee444e7bfb1fdfda8779613815e31392a67a8095a7403411b7bcb5492604f5d35900215740bad0fac")
    
    print("并发发送两个请求，测试优先级...")
    
    # 并发发送两个请求（ceshi1的update_time更晚，应该先处理）
    t1 = threading.Thread(target=send_request, args=("ceshi1", "123456", encrypted_data))
    t2 = threading.Thread(target=send_request, args=("ceshi2", "123456", encrypted_data))
    
    # 同时启动
    t1.start()
    t2.start()
    
    # 等待两个请求都完成
    t1.join()
    t2.join()
    



if __name__ == "__main__":
    main()
