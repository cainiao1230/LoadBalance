import requests
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_server_token():
    """
    获取服务器token并打印
    """
    url = "https://192.0.2.1:api/login"
    params = {
        "username": "ceshi",
        "password": "123456"
    }
    try:
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.raise_for_status()
        data = response.json()
        token = data.get("data", {}).get("token", None)
        print(f"Token: {token}")
        return token
    except Exception as e:
        print(f"获取token失败: {e}")
        return None

def direct_Test(token, data_file_path):
    """
    依次请求解密服务器，统计密钥包和100条数据包解密总耗时
    :param token: 登录token
    :param data_file_path: drone_one_100data.txt 路径
    """

    #url = "https://192.0.2.1/api/yd/decryptl"
    #url = "http://127.0.0.1:5000/api/yd/decryptl"
    url = "http://192.0.2.1:5000/api/yd/decryptl"

    hex_list = []
    with open(data_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('key_packet:'):
                hex_list.append(line.split('key_packet:')[1].strip())
            elif line.startswith('data_packet_'):
                hex_list.append(line.split(':', 1)[1].strip())
    print(f"共需解密 {len(hex_list)} 条数据（含密钥包和数据包）")
    start = time.time()
    for i, hex_data in enumerate(hex_list):
        params = {"hex": hex_data, "token": token}
        try:
            resp = requests.get(url, params=params, timeout=10, verify=False)
            resp.raise_for_status()
            # 可选：打印部分响应内容
            print(f"第{i+1}条解密响应: {resp.json()}")
        except Exception as e:
            print(f"第{i+1}条解密失败: {e}")
    end = time.time()
    print(f"总耗时: {end - start:.2f} 秒")
#测试现在访问阿里的：44.66；19.19；21.91

#改进后：37.35；18.04；23.46
#再改进：

if __name__ == "__main__":
    #token = get_server_token()
    token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiY2VzaGkxICAiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiIwIiwiZXhwIjoxNzcwNjAyMTIwLCJpc3MiOiJBcGlTdG9yZSIsImF1ZCI6IkFwaVN0b3JlIiwianRpIjoiYWM1NWEifQ.k_lyUejnMXoJKum7Re_K60xjYuxscgLQUde4cvqkr80"
  #if token:
    direct_Test(token, r'd:\java-project\Load-balance-gitee\load-balance\tests\drone_one_100data.txt')
