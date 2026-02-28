"""
获取JWT Token并测试解密API的脚本
"""
import requests
import json

# 登录API配置
LOGIN_URL = "https://192.0.2.1/api/login"
DECRYPT_URL = "https://192.0.2.1/api/yd/decryptl"
USERNAME = "xingxun"
PASSWORD = "xingxun123"

# 测试用的十六进制数据（在这里修改）
TEST_HEX = "19cb9ba7f337bebe247a4ccab1fb2dfc5bdeb9e4449ad845bf598af9fabef68ff96b814efb8634abd605d3805e960287cbb17eae4d8aac4a608ab897f828e2dae3a87da65dde132ad68e5eb19471c7dacb9985332cfaa1ba87f2301f6bc94ea9861b3588e177cabe6ef5156787e8d69a86c506e240c8c71cc161df04c46dcdc97091da94171af3cb444485316a68ef7f6a5410815a33334b1cb8075ab581c41c7ba854f6d10d2d87a90615740b846700"  # 示例: "a8379b24f0b1ba62..."

def get_token():
    """获取JWT Token"""
    try:
        print(f"🔐 正在登录... ({USERNAME})")
        
        response = requests.get(
            LOGIN_URL,
            params={
                "username": USERNAME,
                "password": PASSWORD
            },
            timeout=3
        )
        
        print(f"📡 状态码: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        
        print(f"📄 响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data.get("success") and "data" in data and "token" in data["data"]:
            token = data["data"]["token"]
            print(f"\n✅ Token 获取成功!")
            print(f"🔑 Token: {token}")
            print(f"\n📋 完整Token（可复制）：")
            print(token)
            return token
        else:
            print(f"❌ 登录失败: {data.get('msg')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def test_decrypt(token, hex_data):
    """测试解密API
    
    Args:
        token: JWT Token
        hex_data: 十六进制数据（连续字符串，无逗号）
    """
    try:
        print(f"\n🔓 正在测试解密...")
        print(f"📦 十六进制数据: {hex_data[:50]}... (长度: {len(hex_data)})")
        
        response = requests.get(
            DECRYPT_URL,
            params={
                "hex": hex_data,
                "token": token
            },
            timeout=30
        )
        
        print(f"📡 状态码: {response.status_code}")
        print(f"📄 响应内容:")
        
        # 尝试解析JSON
        try:
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        except:
            # 如果不是JSON，直接输出文本
            print(response.text)
            return response.text
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("JWT Token 获取 & 解密测试工具")
    print("=" * 60)
    print()
    
    # 1. 获取Token
    token = get_token()
    
    if not token:
        print("\n" + "=" * 60)
        print("❌ Token获取失败，无法继续测试!")
        print("=" * 60)
        exit(1)
    
    # 2. 测试解密
    if TEST_HEX:
        print("\n" + "-" * 60)
        print("🔓 开始解密测试...")
        
        result = test_decrypt(token, TEST_HEX)
        
        if result:
            print("\n✅ 解密测试完成!")
        else:
            print("\n❌ 解密测试失败!")
    else:
        print("\n⚠️  未设置 TEST_HEX，跳过解密测试")
        print("💡 提示: 在代码中设置 TEST_HEX 变量后即可测试解密")
    
    print("\n" + "=" * 60)
    print("✅ 完成!")
    print("=" * 60)
