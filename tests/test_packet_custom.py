"""
数据包测试脚本
支持测试密钥包去重、数据包处理、无效包拒绝等功能
"""
import requests
import sys
import time


def send_packet(hex_data: str, username: str = "ceshi1", password: str = "123456", description: str = ""):
    """
    测试单个数据包
    
    Args:
        hex_data: 176字节的十六进制数据（可以带逗号、空格等分隔符）
        username: 用户名
        password: 密码
        description: 测试描述
    """
    url = "http://localhost:8765/api/task/quick-submit"
    
    # 清理数据：去除逗号、空格等
    clean_hex = ''.join(c for c in hex_data if c in '0123456789abcdefABCDEF')
    
    # 验证长度
    if len(clean_hex) != 352:  # 176字节 = 352个十六进制字符
        print(f"❌ 错误：数据长度不正确！")
        print(f"   期望: 352个字符 (176字节)")
        print(f"   实际: {len(clean_hex)}个字符 ({len(clean_hex)//2}字节)")
        return None
    
    print("\n" + "=" * 70)
    if description:
        print(f"📋 测试: {description}")
    print("=" * 70)
    print(f"👤 用户: {username}")
    print(f"📦 数据长度: {len(clean_hex)//2} 字节")
    print(f"📤 数据(前40字符): {clean_hex[:40]}...")
    
    try:
        start = time.time()
        params = {
            "username": username,
            "password": password,
            "encrypted_data": clean_hex
        }
        resp = requests.get(url, params=params, timeout=60)
        elapsed = time.time() - start
        
        print(f"\n📥 响应:")
        print(f"   状态码: {resp.status_code}")
        print(f"   耗时: {elapsed:.2f}秒")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   status: {data.get('status')}")
            print(f"   task_id: {data.get('task_id', 'N/A')}")
            
            # 根据不同状态显示信息
            status = data.get('status')
            if status == 'key_exist':
                print(f"   ✅ 密钥已存在，无需重复处理")
            elif status == 'key_gen_busy':
                print(f"   🔄 服务器繁忙，请稍后重试")
            elif status == 'completed':
                print(f"   ✅ 处理完成")
                print(f"   开始时间: {data.get('start_time', 'N/A')}")
                print(f"   完成时间: {data.get('finish_time', 'N/A')}")
                decrypted = data.get('decrypted_data', '')
                if len(str(decrypted)) > 200:
                    print(f"   响应数据(前200字符): {str(decrypted)[:200]}...")
                else:
                    print(f"   响应数据: {decrypted}")
            
            return data
            
        elif resp.status_code == 400:
            print(f"   ❌ 请求错误: {resp.json().get('detail', resp.text)}")
            return None
        elif resp.status_code == 401:
            print(f"   ❌ 认证失败: {resp.json().get('detail', '用户名或密码错误')}")
            return None
        elif resp.status_code == 503:
            print(f"   ⚠️  服务繁忙: {resp.json().get('detail', '队列已满')}")
            return None
        else:
            print(f"   ❌ 未知错误: {resp.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"   ⏱️  请求超时（60秒）")
        return None
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_multiple_packets(hex_data_list: list, username: str = "ceshi1", password: str = "123456", 
                         interval: float = 0.1, description: str = ""):
    """
    用一个账号测试多条数据
    
    Args:
        hex_data_list: 十六进制数据列表
        username: 用户名
        password: 密码
        interval: 每条数据间隔时间（秒），默认0.1秒
        description: 测试描述
    """
    print("\n" + "=" * 70)
    print(f"🔄 批量测试: {description if description else '多条数据测试'}")
    print("=" * 70)
    print(f"👤 用户: {username}")
    print(f"📦 数据条数: {len(hex_data_list)}")
    print(f"⏱️  发送间隔: {interval}秒")
    
    results = []
    
    for i, hex_data in enumerate(hex_data_list, 1):
        print(f"\n{'─'*70}")
        print(f"📨 发送第 {i}/{len(hex_data_list)} 条数据")
        result = send_packet(hex_data, username, password, description=f"第{i}条")
        results.append(result)
        
        # 最后一条不需要等待
        if i < len(hex_data_list):
            time.sleep(interval)
    
    # 统计结果
    print("\n" + "=" * 70)
    print("📊 批量测试统计")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r and r.get('status') == 'completed')
    key_exist_count = sum(1 for r in results if r and r.get('status') == 'key_exist')
    key_busy_count = sum(1 for r in results if r and r.get('status') == 'key_gen_busy')
    error_count = sum(1 for r in results if r is None)
    
    print(f"✅ 成功处理: {success_count}")
    print(f"🔄 密钥忙碌: {key_busy_count}")
    print(f"📋 密钥已存在: {key_exist_count}")
    print(f"❌ 失败/错误: {error_count}")
    print(f"📈 总计: {len(results)}")
    
    return results


def main():
    """主测试流程"""
    print("=" * 70)
    print("🧪 数据包测试工具")
    print("=" * 70)
    
    # ===== 在这里修改你的测试数据 =====
    
    # 示例1: 单条数据测试（数据包）
    test_data_1 = \
        """
,8d,b7,9b,da,f0,c1,2f,8d,8d,b5,52,59,ad,c7,1d,1b,0d,74,61,41,fa,1a,f8,5a,be,26,d0,32,e7,14,d8,1d,39,97,80,59,e6,cb,15,57,e6,a1,bf,ee,11,20,a1,06,0e,d9,8e,f2,f9,11,eb,38,3a,c1,15,64,d5,5b,38,d8,7a,6d,66,f5,b7,0c,fe,c1,6e,ab,5e,9d,e9,45,07,7c,06,07,f6,01,db,93,e0,27,6d,e8,f9,6b,c4,07,2b,7a,cf,38,f9,39,8a,34,c0,b4,6e,62,aa,be,87,03,1f,5f,9a,a4,8f,35,f1,40,74,ae,b1,a8,60,a5,17,dc,ad,c9,70,57,ac,e6,93,3d,40,cc,eb,c4,cf,e8,db,06,00,c4,72,32,71,81,39,2a,a0,51,2e,8e,b6,62,90,9c,78,6a,5d,ee,54,8a,30,ad,5b,ad,02,9d,2d,44,71,47,1d,49,

      """
    # ===== 选择测试模式 =====
    
    # 模式1：单条数据测试（包含去重测试）
    TEST_MODE = "single"  # 改为 "multiple" 可以测试多条数据
    
    if TEST_MODE == "single":
        # 测试1：第一次提交
        print("\n📍 测试场景1：提交数据包")
        result1 = send_packet(test_data_1, description="第一次提交")
        
        if result1:
            # 测试2：立即重复提交相同数据（测试去重）
            print("\n📍 测试场景2：立即重复提交（测试去重）")
            time.sleep(0.5)
            result2 = send_packet(test_data_1, description="重复提交测试")
            
            # 如果是密钥包，应该返回 key_gen_busy 或 key_exist
            if result2:
                status = result2.get('status')
                if status in ['key_gen_busy', 'key_exist']:
                    print(f"\n✅ 去重测试通过：系统正确识别重复的密钥包")
                elif status == 'completed':
                    print(f"\n⚠️  这可能是数据包（不去重）或者第一个任务已处理完成")
    
    elif TEST_MODE == "multiple":
        # 模式2：批量测试多条数据
        # 在这里添加你的多组测试数据
        multiple_data = [
            test_data_1,  # 第一条
            # 在下面添加更多数据，例如：
            # """你的第二条176字节数据...""",
            # """你的第三条176字节数据...""",
        ]
        
        send_multiple_packets(
            multiple_data, 
            username="ceshi1",
            interval=0.1,  # 每条数据间隔0.1秒
            description="批量数据测试"
        )
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    print("\n提示：请修改脚本中的 test_data_1 变量为你的实际数据\n")
    main()
