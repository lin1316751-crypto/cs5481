# 测试目录

本目录包含项目的单元测试和集成测试。

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── test_redis_client.py     # Redis 客户端测试
├── test_data_exporter.py    # 数据导出器测试
└── test_rss_crawler.py      # RSS 爬虫测试
```

## 运行测试

### 安装测试依赖

```bash
pip install pytest pytest-cov pytest-mock
```

### 运行所有测试

```bash
# 在项目根目录运行
pytest tests/

# 带详细输出
pytest tests/ -v

# 带覆盖率报告
pytest tests/ --cov=. --cov-report=html
```

### 运行特定测试

```bash
# 运行单个测试文件
pytest tests/test_redis_client.py

# 运行特定测试类
pytest tests/test_redis_client.py::TestRedisClient

# 运行特定测试方法
pytest tests/test_redis_client.py::TestRedisClient::test_push_data_success
```

### 按标记运行

```bash
# 只运行单元测试
pytest -m unit

# 跳过需要 Redis 的测试
pytest -m "not redis"
```

## 测试说明

### 单元测试

- **test_redis_client.py**: 测试 Redis 连接、数据推送、配额管理等核心功能
- **test_data_exporter.py**: 测试数据导出和队列修剪功能
- **test_rss_crawler.py**: 测试 RSS 解析逻辑（使用 mock）

### Mock 使用

大多数测试使用 `unittest.mock` 来模拟外部依赖（Redis、API 等），无需真实服务即可运行。

### 集成测试

标记为 `@pytest.mark.skip` 的测试需要真实的外部服务（如 Redis），在本地开发时可以启用。

## 扩展测试

### 添加新测试

1. 在 `tests/` 目录创建 `test_<module>.py`
2. 定义测试类 `Test<ClassName>`
3. 编写测试方法 `test_<功能>()`
4. 使用 mock 模拟外部依赖

### 示例

```python
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    def test_something(self):
        # Arrange
        mock_obj = Mock()
        
        # Act
        result = some_function(mock_obj)
        
        # Assert
        assert result == expected_value
```

## CI 集成

可以在 GitHub Actions 中配置自动测试：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ -v
```

## 注意事项

- 测试应该快速且独立
- 使用 mock 避免依赖真实服务
- 每个测试只测试一个功能点
- 测试名称应清晰描述测试内容
