"""
十六进制数据格式化工具
用于将逗号分隔的十六进制数字转换为连续字符串
"""


def remove_commas_from_hex(hex_string: str) -> str:
    """
    去掉十六进制字符串中的逗号，将数字连接在一起
    
    Args:
        hex_string: 逗号分隔的十六进制字符串
                   例如: "2c,42,9b,f4,f3,52"
    
    Returns:
        连续的十六进制字符串
        例如: "2c429bf4f352"
    
    Example:
        >>> hex_data = "2c,42,9b,f4,f3,52,59,be"
        >>> result = remove_commas_from_hex(hex_data)
        >>> print(result)
        2c429bf4f35259be
    """
    # 去掉所有逗号和空格
    return hex_string.replace(",", "").replace(" ", "").strip()


def format_hex_array_to_string(hex_array: list) -> str:
    """
    将十六进制数字数组转换为连续字符串
    
    Args:
        hex_array: 十六进制数字列表
                  例如: [0x2c, 0x42, 0x9b]
    
    Returns:
        连续的十六进制字符串
        例如: "2c429b"
    """
    return "".join(f"{byte:02x}" for byte in hex_array)


if __name__ == "__main__":
    # 测试示例.test_hex_keyPackage和test_hex_dataPackage是已经捷豹出来的
    #test_hex_keyPackage1="8db79bdaf0c12f8d8db55259adc71d1b0d746141fa1af85abe26d032e714d81d39978059e6cb1557e6a1bfee1120a1060ed98ef2f911eb383ac11564d55b38d87a6d66f5b70cfec16eab5e9de945077c0607f601db93e0276de8f96bc4072b7acf38f9398a34c0b46e62aabe87031f5f9aa48f35f14074aeb1a860a517dcadc97057ace6933d40ccebc4cfe8db0600c472327181392aa0512e8eb662909c786a5dee548a30ad5bad029d2d4471471d49"
    test_hex_keyPackage2=""
    #test_hex_dataPackage="98829b5cf3321abe9bff79ca4a9e2d8a6d4e80e45683454528ab27650ff7e9a6882d38c0c78634abd60537f1bc9c5b46b9ecd9ae4d8a8edd60d4cd97f83dca99dca829ef216ac11ed60e5eb8db719f7ccb9985332cfaba274de82e43f8abf2a9cbfd86ea6254ca436e628319879d596186f6d095f122097877e7df04c40b57c97031397815a6b4e342449bd43bf7b7d4a29e7b81fbdd4b4d06b1775a4c4dfa675dd154558ba03985eb0315740b26af12"
    test="98,82,9b,5c,f3,32,1a,be,9b,ff,79,ca,4a,9e,2d,8a,6d,4e,80,e4,56,83,45,45,28,ab,27,65,0f,f7,e9,a6,88,2d,38,c0,c7,86,34,ab,d6,05,37,f1,bc,9c,5b,46,b9,ec,d9,ae,4d,8a,8e,dd,60,d4,cd,97,f8,3d,ca,99,dc,a8,29,ef,21,6a,c1,1e,d6,0e,5e,b8,db,71,9f,7c,cb,99,85,33,2c,fa,ba,27,4d,e8,2e,43,f8,ab,f2,a9,cb,fd,86,ea,62,54,ca,43,6e,62,83,19,87,9d,59,61,86,f6,d0,95,f1,22,09,78,77,e7,df,04,c4,0b,57,c9,70,31,39,78,15,a6,b4,e3,42,44,9b,d4,3b,f7,b7,d4,a2,9e,7b,81,fb,dd,4b,4d,06,b1,77,5a,4c,4d,fa,67,5d,d1,54,55,8b,a0,39,85,eb,03,15,74,0b,26,af,12,"
    result = remove_commas_from_hex(test)
    print("=" * 60)
    print(result)
    print(f"\n数据长度: {len(result)} 字符")
    print("=" * 60)
