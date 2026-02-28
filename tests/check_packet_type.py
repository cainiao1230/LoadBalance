"""
检查数据包类型
"""
from app.packet_parser import parse_packet

# 你的测试数据
test_data = """
ea,33,9b,11,f0,f4,41,73,02,38,ed,5d,77,68,53,89,7b,c9,63,10,55,4e,41,5a,6a,e9,ad,ba,dc,5f,f1,91,0d,89,d0,b0,26,50,f6,8d,76,55,c9,9a,74,2b,cb,e0,2a,ea,4d,6a,6b,fa,54,8c,2d,69,9f,24,d5,e7,44,f2,7a,42,54,9e,03,db,58,e3,37,77,5e,3b,36,75,83,a8,17,2b,be,49,48,42,0e,59,c3,96,19,5e,54,9f,60,8a,5f,a4,94,5f,fe,78,c0,5d,6e,85,f0,66,87,85,32,49,9a,29,c1,ba,ab,78,b2,ae,77,b3,b6,04,45,b3,ab,c9,70,5f,a1,a6,31,ef,58,b4,ef,2a,20,8f,e7,72,e5,45,c6,e0,89,81,24,80,94,6c,32,d9,1e,62,e2,4c,ac,3d,fb,50,54,47,a4,78,00,74,9a,56,7d,e9,71,b7,2c,33
"""

result = parse_packet(test_data)

print("=" * 70)
print("数据包分析")
print("=" * 70)
print(f"第一字节(demask后): {result['first_byte']}")
print(f"包类型: {result['packet_type']}")
print(f"是否为密钥包: {result['is_key_packet']}")
print(f"无人机ID: {result['drone_id']}")
print(f"\ndemask后完整数据(前40字符):")
print(result['demasked_hex'][:80])
print(f"\n原始数据(前40字符):")
print(result['raw_bytes'].hex()[:80])
