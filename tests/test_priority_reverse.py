import requests
import time
import threading


def send_request(username, password, encrypted_data, request_id):
    """发送单个请求并记录时间"""
    url = "http://localhost:8000/api/task/quick-submit"
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
        print(f"{'='*60}")
        print(f"状态: {status}")
        print(f"完成时间: {finish_time}")
        print(f"耗时: {end-start:.2f}秒")
        print(f"响应数据: {decrypted_data[:200]}..." if len(str(decrypted_data)) > 200 else f"响应数据: {decrypted_data}")
        print(f"{'='*60}\n")
    else:
        print(f"[{username}-{request_id}] 请求失败，耗时: {end-start:.2f}秒")
    
    return body.get('finish_time', '') if body else ''


def main():
    encrypted_data = (
        "2c429bf4f35259be8d24b0cabac92df962a56ae466304d45bc0bf0daedf23914fdfec477a58634abd60584a441a97d68822910ae4d8aeb8e60e45f97f8207a4afea8d2d46a46b250d61e5e1c8671f7a8cb9985332cfa337233b857c97671cea9d7a97de9c427caec6ed5ce1087c9bf1986e70ef90781bc15e570df04c40e4ac970fd2b038772ad3a6e4496c99945d92d338d628115cee3a20f45ee5a681bf4f5629a549d8a36b94dfd2715740b68509c"
    )
    
    print("=" * 60)
    print("测试场景：高优先级用户先发请求，低优先级用户后发")
    print("=" * 60)
    print("1. ceshi1（优先级高）先发送30个请求")
    print("2. 等待0.5秒后，ceshi2（优先级低）发送30个请求")
    print("3. 预期：所有ceshi1的请求都应该在ceshi2之前完成")
    print("=" * 60)
    
    threads = []
    ceshi1_results = []
    ceshi2_results = []
    
    # 第一步：ceshi1 连续发送30个请求
    print("\n[阶段1] ceshi1（高优先级）发送30个请求...")
    for i in range(30):
        def make_request(req_id, results_list):
            result = send_request("ceshi1", "123456", encrypted_data, req_id)
            results_list.append((req_id, result))
        
        t = threading.Thread(
            target=make_request, 
            args=(i+1, ceshi1_results)
        )
        threads.append(t)
        t.start()
        time.sleep(0.02)  # 每个请求间隔0.02秒
    
    # 第二步：等待0.5秒
    print(f"\n[等待] 暂停0.5秒...")
    time.sleep(0.5)
    
    # 第三步：ceshi2 发送30个请求
    print("\n[阶段2] ceshi2（低优先级）发送30个请求...")
    for i in range(30):
        def make_request(req_id, results_list):
            result = send_request("ceshi2", "123456", encrypted_data, req_id)
            results_list.append((req_id, result))
        
        t = threading.Thread(
            target=make_request, 
            args=(i+1, ceshi2_results)
        )
        threads.append(t)
        t.start()
        time.sleep(0.02)  # 每个请求间隔0.02秒
    
    # 等待所有请求完成
    print("\n[等待] 等待所有请求完成...")
    for t in threads:
        t.join()
    
    # 分析结果
    print("\n" + "=" * 60)
    print("测试完成！结果分析：")
    print("=" * 60)
    
    # 找出最早和最晚完成的请求
    if ceshi1_results and ceshi2_results:
        ceshi1_times = [t for _, t in ceshi1_results if t]
        ceshi2_times = [t for _, t in ceshi2_results if t]
        
        if ceshi1_times and ceshi2_times:
            ceshi1_latest = max(ceshi1_times)
            ceshi2_earliest = min(ceshi2_times)
            
            print(f"ceshi1（高优先级）最晚完成时间: {ceshi1_latest}")
            print(f"ceshi2（低优先级）最早完成时间: {ceshi2_earliest}")
            
            if ceshi1_latest < ceshi2_earliest:
                print("\n✅ 测试通过！所有高优先级请求都在低优先级请求之前完成")
            else:
                print("\n❌ 测试失败！有低优先级请求在高优先级之前完成")
                print("这可能说明优先级队列没有正常工作")
    
    print(f"\nceshi1 完成数量: {len([t for _, t in ceshi1_results if t])}/{len(ceshi1_results)}")
    print(f"ceshi2 完成数量: {len([t for _, t in ceshi2_results if t])}/{len(ceshi2_results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
