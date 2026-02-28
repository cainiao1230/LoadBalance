import os
from app.packet_parser import demask_for_176_byte, get_packet_type_name, get_drone_id, hex_string_to_bytes

def extract_samples_from_file(file_path, output_path, sample_count=3):
    """
    从数据集中提取 sample_count 个不同无人机的密钥包和每个无人机的3条数据包
    :param file_path: 数据集文件路径
    :param output_path: 输出文件路径
    :param sample_count: 需要的无人机数量
    """
    drone_samples = {}
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
                if drone_id not in drone_samples:
                    drone_samples[drone_id] = {'key': None, 'data': []}
                if packet_type == 'key_packet' and drone_samples[drone_id]['key'] is None:
                    drone_samples[drone_id]['key'] = hex_str
                elif packet_type == 'data_packet' and len(drone_samples[drone_id]['data']) < 3:
                    drone_samples[drone_id]['data'].append(hex_str)
                # 如果已经收集到足够的无人机
                if len([d for d in drone_samples.values() if d['key'] and len(d['data']) == 3]) >= sample_count:
                    break
            except Exception:
                continue
    # 只保留满足条件的无人机
    result = {k: v for k, v in drone_samples.items() if v['key'] and len(v['data']) == 3}
    with open(output_path, 'w') as f:
        for drone_id, v in result.items():
            f.write(f"# drone_id: {drone_id}\n")
            f.write(f"key_packet: {v['key']}\n")
            for i, data in enumerate(v['data']):
                f.write(f"data_packet_{i+1}: {data}\n")
            f.write("\n")
    print(f"已提取 {len(result)} 架无人机样本，结果已保存到 {output_path}")

if __name__ == "__main__":
    # 修改为你的数据集文件路径
    dataset_path = r"C:\Users\Admin\Desktop\星巡\drone.log"
    output_path = r"d:\java-project\Load-balance-gitee\load-balance\tests\drone_samples.txt"
    extract_samples_from_file(dataset_path, output_path, sample_count=3)
