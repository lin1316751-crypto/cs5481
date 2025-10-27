"""
Redis 数据查看工具
用于查看和管理 Redis 中的数据
"""
import json
import yaml
from utils.redis_client import RedisClient
from utils.logger import setup_logger

logger = setup_logger('redis_viewer')


def main():
    """主函数"""
    print("=" * 60)
    print("Redis 数据查看工具")
    print("=" * 60)
    
    # 加载配置
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("错误: config.yaml 不存在，请先创建配置文件")
        return
    
    # 连接 Redis
    try:
        redis_client = RedisClient(**config['redis'])
    except Exception as e:
        print(f"错误: 无法连接 Redis - {e}")
        return
    
    while True:
        print("\n" + "=" * 60)
        print("选项:")
        print("1. 查看队列长度")
        print("2. 查看最新数据（前10条）")
        print("3. 查看最新数据（前50条）")
        print("4. 按来源统计数据")
        print("5. 导出数据到文件")
        print("0. 退出")
        print("=" * 60)
        
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            length = redis_client.get_queue_length()
            print(f"\n当前队列长度: {length}")
        
        elif choice == '2':
            show_data(redis_client, 10)
        
        elif choice == '3':
            show_data(redis_client, 50)
        
        elif choice == '4':
            show_statistics(redis_client)
        
        elif choice == '5':
            export_data(redis_client)
        
        elif choice == '0':
            print("退出程序")
            break
        
        else:
            print("无效选项，请重新选择")
    
    redis_client.close()


def show_data(redis_client, count):
    """显示数据"""
    print(f"\n最新 {count} 条数据:")
    print("-" * 60)
    
    data_list = redis_client.peek_data(count)
    
    for i, data in enumerate(data_list, 1):
        print(f"\n[{i}] 来源: {data.get('source')}")
        print(f"    时间: {data.get('timestamp')}")
        print(f"    URL: {data.get('url')}")
        text = data.get('text', '')
        if len(text) > 100:
            text = text[:100] + "..."
        print(f"    内容: {text}")
    
    print(f"\n总共显示 {len(data_list)} 条数据")


def show_statistics(redis_client):
    """显示统计信息"""
    print("\n数据来源统计:")
    print("-" * 60)
    
    length = redis_client.get_queue_length()
    
    # 获取所有数据进行统计（如果数据量大，可以只取样）
    sample_size = min(1000, length)
    data_list = redis_client.peek_data(sample_size)
    
    # 统计各来源数量
    source_count = {}
    for data in data_list:
        source = data.get('source', 'unknown')
        source_count[source] = source_count.get(source, 0) + 1
    
    # 显示统计结果
    for source, count in sorted(source_count.items()):
        percentage = (count / len(data_list)) * 100 if data_list else 0
        print(f"{source:20s}: {count:6d} ({percentage:5.2f}%)")
    
    print(f"\n统计样本: {len(data_list)} / {length}")


def export_data(redis_client):
    """导出数据到文件"""
    count = input("输入要导出的数据条数（默认100）: ").strip()
    try:
        count = int(count) if count else 100
    except ValueError:
        count = 100
    
    filename = input("输入导出文件名（默认data_export.json）: ").strip()
    if not filename:
        filename = "data_export.json"
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    print(f"\n正在导出 {count} 条数据到 {filename}...")
    
    data_list = redis_client.peek_data(count)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        print(f"成功导出 {len(data_list)} 条数据到 {filename}")
    except Exception as e:
        print(f"导出失败: {e}")


if __name__ == '__main__':
    main()
