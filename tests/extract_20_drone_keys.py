import os
from app.packet_parser import demask_for_176_byte, get_packet_type_name, get_drone_id, hex_string_to_bytes

def extract_n_drone_keys(file_path, output_path, n=20):
    """
    从数据集中提取 n 个不同无人机的密钥包
    :param file_path: 数据集文件路径
    :param output_path: 输出文件路径
    :param n: 需要的无人机数量
    """
    drone_keys = {}
    with open(file_path, 'r') as f:
        for line in f:
            hex_str = line.strip()
            if len(hex_str) != 352:
                continue
            try:
                raw_bytes = bytes.fromhex(hex_str)
                demasked = demask_for_176_byte(raw_bytes)
                packet_type = get_packet_type_name(demasked)
                drone_id = get_drone_id(demasked)
                if not drone_id:
                    continue
                if packet_type == 'key_packet' and drone_id not in drone_keys:
                    drone_keys[drone_id] = hex_str
                if len(drone_keys) >= n:
                    break
            except Exception:
                continue
    with open(output_path, 'w') as f:
        for drone_id, key_hex in drone_keys.items():
            f.write(f"# drone_id: {drone_id}\n")
            f.write(f"key_packet: {key_hex}\n\n")
    print(f"已提取 {len(drone_keys)} 架无人机的密钥包，结果已保存到 {output_path}")

if __name__ == "__main__":
    dataset_path = r"C:\Users\Admin\Desktop\星巡\drone.log"
    output_path = r"d:\java-project\Load-balance-gitee\load-balance\tests\drone_20keys.txt"
    extract_n_drone_keys(dataset_path, output_path, n=20)
