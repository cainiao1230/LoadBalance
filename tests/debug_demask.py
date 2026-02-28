"""
调试解包算法
验证 demask_for_176_byte() 是否正确
"""
from app.packet_parser import demask_for_176_byte, parse_packet

# 你提供的原始加密数据
test_data = """
ea,33,9b,11,f0,f4,41,73,02,38,ed,5d,77,68,53,89,7b,c9,63,10,55,4e,41,5a,6a,e9,ad,ba,dc,5f,f1,91,0d,89,d0,b0,26,50,f6,8d,76,55,c9,9a,74,2b,cb,e0,2a,ea,4d,6a,6b,fa,54,8c,2d,69,9f,24,d5,e7,44,f2,7a,42,54,9e,03,db,58,e3,37,77,5e,3b,36,75,83,a8,17,2b,be,49,48,42,0e,59,c3,96,19,5e,54,9f,60,8a,5f,a4,94,5f,fe,78,c0,5d,6e,85,f0,66,87,85,32,49,9a,29,c1,ba,ab,78,b2,ae,77,b3,b6,04,45,b3,ab,c9,70,5f,a1,a6,31,ef,58,b4,ef,2a,20,8f,e7,72,e5,45,c6,e0,89,81,24,80,94,6c,32,d9,1e,62,e2,4c,ac,3d,fb,50,54,47,a4,78,00,74,9a,56,7d,e9,71,b7,2c,33
"""

# # 你说的正确解密结果
# expected_result = "8710494e4e4650602a60bfce83e85b5339d9706d008b1c0aed87088489e11ee976781f4fa1639d8362109feda203dfc577ae6b18848f4229c62cf51bc455b00e14e3bcc07eb770a42dd08a9c931352c4b2c2680296064d8dc6e2211bc8b6f288e5b406f756a8a4e238e56ad01719eb22f245a7de7ae599227830c57ff6ce189a7fcacf2000c6274700b414000000000000000000000000000000000000000000000000000000000000007a38bbd35730fe"

print("=" * 80)
print("🔍 解包算法验证")
print("=" * 80)

# 清理数据
clean_hex = ''.join(c for c in test_data if c in '0123456789abcdefABCDEF')
raw_bytes = bytes.fromhex(clean_hex)

print(f"\n📥 原始加密数据（前40字符）: {clean_hex[:40]}...")
print(f"   长度: {len(raw_bytes)} 字节")

# 使用我们的解包算法
demasked = demask_for_176_byte(raw_bytes)
demasked_hex = demasked.hex()
print(f"\n📤 解包后数据: {demasked_hex}.")

result = parse_packet(clean_hex)
print(f"是否有效: {result['is_valid']}")
print(f"包类型: {result['packet_type']}")
print(f"是否为密钥包: {result['is_key_packet']}")
print(f"第一个字节: {result['first_byte']}")
print(f"无人机ID: {result['drone_id']}")

print("\n" + "=" * 80)
