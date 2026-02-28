import requests
import time
import threading


def send_request(username, password, encrypted_data, request_id):
    """发送单个请求并记录时间"""
    url = "http://192.0.2.1:8000/api/task/quick-submit"
    params = {
        "username": username,
        "password": password,
        "encrypted_data": encrypted_data,
    }
    
    start = time.time()
    resp = requests.get(url, params=params, timeout=60)
    end = time.time()
    
    try:
        body = resp.json()
    except Exception:
        body = None

    if body:
        finish_time = body.get('finish_time', '')
        decrypted_data = body.get('decrypted_data', '')
        status = body.get('status', '')
        
        print(f"\n{'='*60}")
        print(f"[{username}-{request_id}] 响应结果")
        print(decrypted_data)
        print(f"完成时间: {finish_time}")
        print(f"{'='*60}\n")
    else:
        print(f"[{username}-{request_id}] 请求失败，耗时: {end-start:.2f}秒")
    
    return body.get('finish_time', '') if body else ''


def main():
    encrypted_data = (
        "77e19b17f33dfabeba6fddca67e12d9a8ccd7be4e49a56"
        "45da1a000ccb683883ebf1633b188634abd605962bd"
        "1e24aa38fb2c9ae4d8a2a68607edf97f87c115cbba87"
        "05e7e4cee90d63c5eb07071c0c5cb9985332cfa9c2aabf"
        "2cdc135b640a9873770d6127dca376ef5949c878d1d2d86"
        "3d5677408f10bb2ddadf04c4f6adc9706e2e36d9f9c9dee"
        "444e7bfb1fdfda8779613815e31392a67a8095a74"
        "03411b7bcb5492604f5d35900215740bad0fac"
    )
    
    print("=" * 60)
    print("测试场景：低优先级用户先发请求，高优先级用户插队")
    print("=" * 60)
    print("1. ceshi2（优先级低）先发送50个请求")
    print("2. 等待0.5秒后，ceshi1（优先级高）发送1个请求")
    print("3. 预期：ceshi1会插队到ceshi2未处理的请求前面")
    print("=" * 60)
    
    threads = []
    
    # 第一步：ceshi2 连续发送50个请求（制造队列积压）
    print("\n[阶段1] ceshi2 发送50个请求...")
    for i in range(50):
        t = threading.Thread(
            target=send_request, 
            args=("ceshi2", "123456", encrypted_data, i+1)
        )
        threads.append(t)
        t.start()
        time.sleep(0.02)  # 每个请求间隔0.02秒，快速发送
    
    # 第二步：等待0.5秒（让部分请求进入队列，但还有大量积压）
    print(f"\n[等待] 暂停0.5秒...")
    time.sleep(0.5)
    
    # 第三步：ceshi1 发送1个请求（应该插队）
    print("\n[阶段2] ceshi1 发送插队请求...")
    t = threading.Thread(
        target=send_request, 
        args=("ceshi1", "123456", encrypted_data, "VIP")
    )
    threads.append(t)
    t.start()
    
    # 等待所有请求完成
    for t in threads:
        t.join()



if __name__ == "__main__":
    main()
