"""
一键导出 Redis 数据到本地文件
用于分享数据给数据分析、清洗团队
"""
import os
import sys
import json
from datetime import datetime
import redis
import yaml

def load_config():
    """加载配置文件"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def export_redis_data():
    """导出 Redis 所有数据到 JSON 文件"""
    print("=" * 60)
    print("Redis 数据一键导出工具")
    print("=" * 60)
    print()
    
    # 1. 连接 Redis
    config = load_config()
    redis_config = config['redis']
    
    print(f"[1/4] 连接 Redis ({redis_config['host']}:{redis_config['port']})...")
    try:
        r = redis.Redis(
            host=redis_config['host'],
            port=redis_config['port'],
            password=redis_config.get('password'),
            decode_responses=True
        )
        r.ping()
        print("✓ Redis 连接成功")
    except Exception as e:
        print(f"✗ Redis 连接失败: {e}")
        print("\n请先启动 Redis:")
        print("  .\\start_redis.bat")
        return False
    
    # 2. 获取队列数据
    print("\n[2/4] 获取队列数据...")
    # 修复: 使用正确的配置键名 queue_name
    queue_key = config['redis'].get('queue_name', 'data_queue')
    total = r.llen(queue_key)
    
    if total == 0:
        print("✗ Redis 队列为空，没有数据可导出")
        print("\n建议:")
        print("  1. 运行爬虫采集数据: .\\run.bat")
        print("  2. 选择菜单: 2. Run crawler once")
        return False
    
    print(f"✓ 找到 {total:,} 条数据")
    
    # 3. 读取所有数据
    print("\n[3/4] 读取数据...")
    all_data = []
    batch_size = 1000
    
    for i in range(0, total, batch_size):
        batch = r.lrange(queue_key, i, min(i + batch_size - 1, total - 1))
        for item in batch:
            try:
                all_data.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        
        progress = min(i + batch_size, total)
        print(f"  进度: {progress:,}/{total:,} ({progress/total*100:.1f}%)", end='\r')
    
    print(f"\n✓ 成功读取 {len(all_data):,} 条有效数据")
    
    # 4. 导出到文件
    print("\n[4/4] 导出到文件...")
    
    # 创建导出目录
    export_dir = "data_exports/manual_export"
    os.makedirs(export_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 导出完整 JSON
    json_file = os.path.join(export_dir, f"redis_export_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    file_size_mb = os.path.getsize(json_file) / (1024 * 1024)
    print(f"✓ JSON 文件: {json_file}")
    print(f"  大小: {file_size_mb:.2f} MB")
    
    # 导出 JSONL (每行一条,方便分析工具读取)
    jsonl_file = os.path.join(export_dir, f"redis_export_{timestamp}.jsonl")
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    file_size_mb = os.path.getsize(jsonl_file) / (1024 * 1024)
    print(f"✓ JSONL 文件: {jsonl_file}")
    print(f"  大小: {file_size_mb:.2f} MB")
    
    # 按数据源统计
    print("\n" + "=" * 60)
    print("数据源统计:")
    print("=" * 60)
    source_counts = {}
    for item in all_data:
        source = item.get('source', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
    
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(all_data) * 100
        print(f"  {source:12s}: {count:6,} 条 ({percentage:5.1f}%)")
    
    # 导出元数据
    print("\n" + "=" * 60)
    print("导出信息:")
    print("=" * 60)
    metadata = {
        "export_time": datetime.now().isoformat(),
        "total_records": len(all_data),
        "source_distribution": source_counts,
        "files": {
            "json": json_file,
            "jsonl": jsonl_file
        }
    }
    
    metadata_file = os.path.join(export_dir, f"export_metadata_{timestamp}.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"导出目录: {os.path.abspath(export_dir)}")
    print(f"总记录数: {len(all_data):,} 条")
    print(f"元数据文件: {metadata_file}")
    
    print("\n" + "=" * 60)
    print("✓ 导出完成！")
    print("=" * 60)
    print("\n可以将以下文件分享给数据分析团队:")
    print(f"  • {json_file}")
    print(f"  • {jsonl_file}")
    print(f"  • {metadata_file}")
    
    print("\n使用建议:")
    print("  • JSON 格式: 适合查看、编辑、可视化")
    print("  • JSONL 格式: 适合流式处理、pandas 读取")
    print("\nPython 读取示例:")
    print("  import pandas as pd")
    print(f"  df = pd.read_json('{jsonl_file}', lines=True)")
    print("  print(df.head())")
    
    return True

if __name__ == "__main__":
    try:
        success = export_redis_data()
        if success:
            input("\n按 Enter 键退出...")
            sys.exit(0)
        else:
            input("\n按 Enter 键退出...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✗ 用户取消导出")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")
        sys.exit(1)
