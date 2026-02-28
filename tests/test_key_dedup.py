"""
测试密钥包去重功能
"""
import requests
import time


def test_key_packet_dedup():
    """测试密钥包去重逻辑"""
    url = "http://localhost:8000/api/task/quick-submit"
    
    # 使用你提供的176字节数据（解包后第一字节是0x87，是数据包）
    # 为了测试密钥包，我们需要一个第一字节是0xa3或0xaa的数据
    # 这里先用现有数据测试
    test_data = "2c,42,9b,f4,f3,52,59,be,8d,24,b0,ca,ba,c9,2d,f9,62,a5,6a,e4,66,30,4d,45,bc,0b,f0,da,ed,f2,39,14,fd,fe,c4,77,a5,86,34,ab,d6,05,84,a4,41,a9,7d,68,82,29,10,ae,4d,8a,eb,8e,60,e4,5f,97,f8,20,7a,4a,fe,a8,d2,d4,6a,46,b2,50,d6,1e,5e,1c,86,71,f7,a8,cb,99,85,33,2c,fa,33,72,33,b8,57,c9,76,71,ce,a9,d7,a9,7d,e9,c4,27,ca,ec,6e,d5,ce,10,87,c9,bf,19,86,e7,0e,f9,07,81,bc,15,e5,70,df,04,c4,0e,4a,c9,70,fd,2b,03,87,72,ad,3a,6e,44,96,c9,99,45,d9,2d,33,8d,62,81,15,ce,e3,a2,0f,45,ee,5a,68,1b,f4,f5,62,9a,54,9d,8a,36,b9,4d,fd,27,15,74,0b,68,50,9c"
    
    # 去掉逗号
    clean_data = test_data.replace(",", "")
    
    params = {
        "username": "ceshi1",
        "password": "123456",
        "encrypted_data": clean_data
    }
    
    print("=" * 60)
    print("测试数据包处理（0x87 = 数据包）")
    print("=" * 60)
    
    # 第一次请求
    print("\n发送第一个请求...")
    resp1 = requests.get(url, params=params, timeout=60)
    print(f"状态码: {resp1.status_code}")
    if resp1.status_code == 200:
        data = resp1.json()
        print(f"响应: status={data.get('status')}, task_id={data.get('task_id')}")
        print(f"数据: {data.get('decrypted_data', '')[:100]}...")
    else:
        print(f"错误: {resp1.text}")
    
    print("\n" + "=" * 60)
    print("说明：")
    print("- 当前测试数据解包后第一字节是 0x87（数据包）")
    print("- 数据包会直接排队处理，不做去重")
    print("- 如需测试密钥包去重，需要提供第一字节为 0xa3 或 0xaa 的数据")
    print("=" * 60)


def test_invalid_packet():
    """测试无效数据包"""
    url = "http://localhost:8000/api/task/quick-submit"
    
    # 构造一个第一字节为0xff的无效包（去掉逗号后的十六进制）
    # 假设原始数据第一个字节经过解包后变成0xff
    invalid_data = "ff" * 176  # 176字节的0xff
    
    params = {
        "username": "ceshi1",
        "password": "123456",
        "encrypted_data": invalid_data
    }
    
    print("\n" + "=" * 60)
    print("测试无效数据包（应返回 useless packet）")
    print("=" * 60)
    
    resp = requests.get(url, params=params, timeout=10)
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.text}")
    
    if resp.status_code == 400:
        print("✅ 正确拒绝了无效数据包")
    else:
        print("❌ 未能正确识别无效数据包")


if __name__ == "__main__":
    print("密钥包去重功能测试\n")
    
    try:
        test_key_packet_dedup()
        time.sleep(1)
        test_invalid_packet()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
