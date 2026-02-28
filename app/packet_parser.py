"""
数据包解包模块
用于处理176字节的密钥包和数据包
"""


def demask_for_176_byte(x: bytes) -> bytes:
    """
    对176字节数据进行解包处理（demask + 重排列）
    
    处理流程:
    1. 对输入的每个字节与mask数组进行XOR操作
    2. 根据interlIdx数组重新排列字节位置
    
    Args:
        x: 176字节的输入数据
    
    Returns:
        处理后的176字节数据
    
    Raises:
        ValueError: 如果输入数据长度不是176字节
    """
    if len(x) != 176:
        raise ValueError(f"Input data must be exactly 176 bytes, got {len(x)}")
    
    # 重排列索引数组
    interl_idx = [
        101, 48, 167, 63, 1, 40, 27, 171, 74, 28, 117, 159, 21, 126, 138, 175,
        114, 125, 37, 149, 100, 110, 122, 4, 116, 42, 111, 174, 50, 57, 86, 107,
        83, 132, 95, 108, 47, 161, 148, 145, 141, 19, 98, 44, 87, 24, 137, 173,
        129, 55, 92, 163, 158, 153, 12, 93, 144, 103, 123, 155, 0, 30, 72, 109,
        79, 140, 61, 73, 99, 124, 118, 71, 146, 75, 166, 10, 39, 154, 14, 89,
        150, 18, 156, 172, 139, 151, 49, 59, 115, 7, 38, 58, 60, 128, 106, 162,
        68, 113, 17, 91, 15, 76, 2, 120, 168, 9, 84, 46, 131, 105, 85, 41, 3,
        134, 20, 77, 8, 104, 56, 90, 64, 94, 160, 152, 142, 52, 45, 164, 165,
        70, 97, 29, 67, 54, 51, 80, 121, 147, 35, 69, 31, 33, 22, 11, 66, 96,
        81, 130, 32, 25, 65, 127, 82, 119, 102, 170, 16, 88, 62, 136, 6, 36, 5,
        26, 34, 133, 43, 78, 112, 135, 143, 157, 169, 23, 53, 13
    ]
    
    # XOR掩码数组
    mask = bytes([
        0xf2, 0x3b, 0x9b, 0x7c, 0xe3, 0xc2, 0x74, 0x05, 0xd1, 0x71, 0x9d, 0xca,
        0xeb, 0xbc, 0x2d, 0x67, 0xef, 0xea, 0x69, 0xe4, 0x0f, 0x5a, 0xcf, 0x03,
        0x23, 0x34, 0x33, 0x9a, 0x45, 0x33, 0x04, 0xbe, 0x71, 0xee, 0x77, 0x6b,
        0xd8, 0x86, 0x34, 0xab, 0xd6, 0x05, 0xae, 0x61, 0xd4, 0x80, 0xb5, 0x6d,
        0x4e, 0x30, 0x31, 0xae, 0x4d, 0x8a, 0x26, 0xb2, 0x60, 0xdb, 0xda, 0x97,
        0x7f, 0xe5, 0xd2, 0xa4, 0xd1, 0xa8, 0x57, 0x4a, 0x57, 0x88, 0xb9, 0x4f,
        0xd6, 0x91, 0x5e, 0xb3, 0x8b, 0x71, 0xb1, 0x9e, 0xcb, 0xf4, 0x85, 0xe0,
        0x2c, 0xfa, 0x45, 0x40, 0xdf, 0xbc, 0x23, 0x03, 0xe4, 0x33, 0x4c, 0xa9,
        0x49, 0x78, 0x11, 0xfc, 0x95, 0x6c, 0x83, 0x55, 0x6e, 0x3a, 0x94, 0xc2,
        0x87, 0xa3, 0x35, 0x61, 0xc8, 0xae, 0x76, 0x91, 0xcb, 0x0f, 0x9a, 0x0d,
        0x6a, 0x4e, 0xdf, 0x04, 0xc4, 0xf8, 0xfc, 0xc9, 0x70, 0x7f, 0x37, 0xa4,
        0x52, 0xf5, 0xb9, 0x69, 0xbe, 0x44, 0x70, 0xee, 0xae, 0x36, 0xd6, 0xa0,
        0x22, 0x35, 0x9b, 0xa1, 0x5e, 0x93, 0x73, 0x0b, 0x07, 0x50, 0x03, 0x62,
        0xae, 0x18, 0x09, 0x9c, 0x9b, 0x04, 0x04, 0x30, 0x96, 0x0f, 0x5e, 0xa1,
        0xb7, 0xb1, 0x15, 0x74, 0x71, 0x5a, 0x27, 0xac
    ])
    
    # 步骤1: XOR操作
    tmp = bytearray(176)
    for i in range(176):
        tmp[i] = x[i] ^ mask[i]
    
    # 步骤2: 根据索引重排列
    out = bytearray(176)
    for i in range(176):
        out[interl_idx[i]] = tmp[i]
    
    return bytes(out)


def hex_string_to_bytes(hex_str: str) -> bytes:
    """
    将十六进制字符串转换为字节数组
    
    Args:
        hex_str: 十六进制字符串（可以带逗号、空格等分隔符）
    
    Returns:
        字节数组
    """
    # 去除所有非十六进制字符
    clean_hex = ''.join(c for c in hex_str if c in '0123456789abcdefABCDEF')
    return bytes.fromhex(clean_hex)


def is_valid_packet(data: bytes) -> bool:
    """
    检查是否为有效数据包
    
    Args:
        data: 解包后的176字节数据
    
    Returns:
        True表示有效，False表示无效（应丢弃）
    """
    if len(data) < 1:
        return False
    
    first_byte = data[0]
    # 有效的第一字节：0xa3, 0xaa (密钥包) 或 0x80, 0x87 (数据包)
    return first_byte in (0xa3, 0xaa, 0x80, 0x87)


def is_key_packet(data: bytes) -> bool:
    """
    判断是否为密钥包（计算量大）
    
    根据解包后数据的第一个字节判断：
    - 0xa3 或 0xaa: 密钥包
    - 0x80 或 0x87: 数据包
    
    Args:
        data: 解包后的176字节数据
    
    Returns:
        True表示密钥包，False表示数据包
    """
    if len(data) < 1:
        return False
    
    first_byte = data[0]
    return first_byte in (0xa3, 0xaa)


def get_drone_id(data: bytes) -> str:
    """
    提取无人机ID（从0开始计数，第6-9字节，共4字节）
    
    无人机ID是临时唯一标识（hash_code），只有在无人机开关机时才会变化
    
    Args:
        data: 解包后的176字节数据
    
    Returns:
        无人机ID的十六进制字符串（8位hex = 4字节 = uint32）
    """
    if len(data) < 10:
        return ""
    
    # 从0开始计数，第6-9字节（索引6,7,8,9），共4字节
    drone_id_bytes = data[6:10]
    return drone_id_bytes.hex()


def get_packet_type_name(data: bytes) -> str:
    """
    获取数据包类型名称
    
    Args:
        data: 解包后的176字节数据
    
    Returns:
        "key_packet" | "data_packet" | "useless_packet"
    """
    if not is_valid_packet(data):
        return "useless_packet"
    
    if is_key_packet(data):
        return "key_packet"
    else:
        return "data_packet"


def parse_packet(encrypted_hex: str) -> dict:
    """
    解析数据包（完整流程），优化版：只计算必要字段
    
    Args:
        encrypted_hex: 十六进制字符串（可以是逗号分隔或连续）
    
    Returns:
        包含以下字段的字典:
        - raw_bytes: 原始字节数组（176字节，用于发送给解密服务器）
        - is_valid: 是否为有效包（True/False）
        - packet_type: 数据包类型 ("key_packet" | "data_packet" | "useless_packet")
        - is_key_packet: 是否为密钥包（仅在有效时有意义）
        - drone_id: 无人机ID（8位hex字符串，用于负载均衡路由）
    """
    # 转换为字节
    raw_bytes = hex_string_to_bytes(encrypted_hex)
    
    if len(raw_bytes) != 176:
        raise ValueError(f"The data packet must be 176 bytes, actual length: {len(raw_bytes)}")
    
    # 根据解包函数得出解包后的176字节数据
    demasked = demask_for_176_byte(raw_bytes)
    
    # 判断包类型（只计算路由必需的信息）
    is_valid = is_valid_packet(demasked)
    packet_type = get_packet_type_name(demasked)
    is_key = is_key_packet(demasked) if is_valid else False
    drone_id = get_drone_id(demasked) if is_valid else ""
    
    return {
        "raw_bytes": raw_bytes,              # 原始数据（发给解密服务器）
        "is_valid": is_valid,                # 是否有效
        "packet_type": packet_type,          # 包类型
        "is_key_packet": is_key,             # 是否密钥包
        "drone_id": drone_id,                # 无人机ID（路由key）
    }


if __name__ == "__main__":
    # 测试示例
    print("=" * 60)
    print("176字节数据包解包工具")
    print("=" * 60)
    
    # 测试数据
    test_hex = "2c,42,9b,f4,f3,52,59,be,8d,24,b0,ca,ba,c9,2d,f9,62,a5,6a,e4,66,30,4d,45,bc,0b,f0,da,ed,f2,39,14,fd,fe,c4,77,a5,86,34,ab,d6,05,84,a4,41,a9,7d,68,82,29,10,ae,4d,8a,eb,8e,60,e4,5f,97,f8,20,7a,4a,fe,a8,d2,d4,6a,46,b2,50,d6,1e,5e,1c,86,71,f7,a8,cb,99,85,33,2c,fa,33,72,33,b8,57,c9,76,71,ce,a9,d7,a9,7d,e9,c4,27,ca,ec,6e,d5,ce,10,87,c9,bf,19,86,e7,0e,f9,07,81,bc,15,e5,70,df,04,c4,0e,4a,c9,70,fd,2b,03,87,72,ad,3a,6e,44,96,c9,99,45,d9,2d,33,8d,62,81,15,ce,e3,a2,0f,45,ee,5a,68,1b,f4,f5,62,9a,54,9d,8a,36,b9,4d,fd,27,15,74,0b,68,50,9c"
    
    try:
        result = parse_packet(test_hex)
        
        print(f"\n原始数据长度: {len(result['raw_bytes'])} 字节")
        print(f"原始数据(hex): {result['raw_bytes'].hex()[:100]}...")
        
        print(f"\n解包后长度: {result['length']} 字节")
        print(f"解包后(hex): {result['demasked_hex'][:100]}...")
        
        print(f"\n数据包分析:")
        print(f"  第一字节: {result['first_byte']}")
        print(f"  是否有效: {result['is_valid']}")
        print(f"  包类型: {result['packet_type']}")
        
        if result['is_valid']:
            print(f"  是否为密钥包: {result['is_key_packet']} ({'计算量大' if result['is_key_packet'] else '计算量小'})")
            print(f"  无人机ID: {result['drone_id']}")
        else:
            print(f"  ⚠️  无效数据包，应丢弃")
        
        print(f"\n完整解包结果(hex):")
        print(result['demasked_hex'])



        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
