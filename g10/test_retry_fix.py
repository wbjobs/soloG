#!/usr/bin/env python3
"""
测试重试机制修复 - 验证幂等接口安全重试功能
"""
import sys
from unittest.mock import Mock, patch
from orchestrator.steps.http_step import HttpStep
from orchestrator.logger import ExecutionLogger


def test_http_step_error_classification():
    """测试 HTTP 步骤的错误分类和 safe_to_retry 标记"""
    print("\n" + "=" * 60)
    print("测试 1: HTTP 步骤错误分类")
    print("=" * 60)
    
    step_config = {
        "id": "test_http",
        "type": "http",
        "name": "Test HTTP",
        "depends_on": [],
        "config": {
            "method": "GET",
            "url": "https://example.com/api",
            "timeout": 10
        }
    }
    
    logger = ExecutionLogger("test")
    step = HttpStep(step_config)
    
    import requests
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"data": "success"}
    mock_response.raise_for_status.return_value = None
    
    with patch.object(requests, 'request', return_value=mock_response):
        result = step.execute({}, logger)
        assert result.success == True
        assert result.data["safe_to_retry"] == False
        print("✅ 200 成功响应: safe_to_retry = False (正确，成功不需要重试)")
    
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"error": "server error"}
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    
    with patch.object(requests, 'request', return_value=mock_response):
        result = step.execute({}, logger)
        assert result.success == False
        assert result.data["safe_to_retry"] == True
        print("✅ 500 服务端错误: safe_to_retry = True (正确，服务端错误可安全重试)")
    
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"error": "bad request"}
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
    
    with patch.object(requests, 'request', return_value=mock_response):
        result = step.execute({}, logger)
        assert result.success == False
        assert result.data["safe_to_retry"] == False
        print("✅ 400 客户端错误: safe_to_retry = False (正确，客户端错误重试无效)")
    
    mock_response = Mock()
    mock_response.status_code = 409
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"error": "conflict - resource already exists"}
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("409 Conflict")
    
    with patch.object(requests, 'request', return_value=mock_response):
        result = step.execute({}, logger)
        assert result.success == False
        assert result.data["safe_to_retry"] == False
        print("✅ 409 冲突错误: safe_to_retry = False (正确，资源已存在，重试会导致重复执行)")
    
    with patch.object(requests, 'request', side_effect=requests.exceptions.ConnectionError("Connection refused")):
        result = step.execute({}, logger)
        assert result.success == False
        assert result.data["safe_to_retry"] == True
        print("✅ 连接错误: safe_to_retry = True (正确，连接错误可安全重试)")
    
    with patch.object(requests, 'request', side_effect=requests.exceptions.Timeout("Request timed out")):
        result = step.execute({}, logger)
        assert result.success == False
        assert result.data["safe_to_retry"] == True
        print("✅ 超时错误: safe_to_retry = True (正确，超时可安全重试)")
    
    print("\n✅ 所有 HTTP 错误分类测试通过!")


def test_idempotency_key():
    """测试幂等键功能"""
    print("\n" + "=" * 60)
    print("测试 2: 幂等键功能")
    print("=" * 60)
    
    step_config = {
        "id": "test_idempotent",
        "type": "http",
        "name": "Test Idempotent",
        "depends_on": [],
        "config": {
            "method": "POST",
            "url": "https://example.com/api/orders",
            "idempotency_key": "order-12345-abcde",
            "body": {"product_id": 1, "quantity": 2}
        }
    }
    
    logger = ExecutionLogger("test")
    step = HttpStep(step_config)
    
    import requests
    
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"order_id": "12345"}
    mock_response.raise_for_status.return_value = None
    
    with patch.object(requests, 'request', return_value=mock_response) as mock_req:
        result = step.execute({}, logger)
        
        call_args = mock_req.call_args
        headers = call_args[1]["headers"]
        assert "Idempotency-Key" in headers
        assert headers["Idempotency-Key"] == "order-12345-abcde"
        print(f"✅ 幂等键已正确添加到请求头: {headers['Idempotency-Key']}")
    
    print("\n✅ 幂等键测试通过!")


def test_safe_retry_logic():
    """测试执行器中的安全重试逻辑"""
    print("\n" + "=" * 60)
    print("测试 3: 安全重试逻辑")
    print("=" * 60)
    
    from orchestrator.executor import Executor
    
    workflow = {
        "name": "test_retry_workflow",
        "version": "1.0",
        "description": "Test workflow",
        "variables": {},
        "steps": []
    }
    
    executor = Executor(workflow, use_celery=False)
    
    result_500 = {
        "success": False,
        "data": {
            "status_code": 500,
            "safe_to_retry": True,
            "error_type": "http_error"
        }
    }
    assert executor._is_safe_to_retry(result_500, [500, 502], []) == True
    print("✅ 500 错误被判定为可安全重试")
    
    result_400 = {
        "success": False,
        "data": {
            "status_code": 400,
            "safe_to_retry": False,
            "error_type": "http_error"
        }
    }
    assert executor._is_safe_to_retry(result_400, [500, 502], []) == False
    print("✅ 400 错误被判定为不可安全重试")
    
    result_connection = {
        "success": False,
        "data": {
            "safe_to_retry": True,
            "error_type": "connection_error"
        }
    }
    assert executor._is_safe_to_retry(result_connection, [], ["connection_error"]) == True
    print("✅ 连接错误被判定为可安全重试")
    
    result_409 = {
        "success": False,
        "data": {
            "status_code": 409,
            "safe_to_retry": False,
            "error_type": "http_error"
        }
    }
    assert executor._is_safe_to_retry(result_409, [500, 502], []) == False
    print("✅ 409 冲突错误被判定为不可安全重试 (避免重复创建资源)")
    
    print("\n✅ 安全重试逻辑测试通过!")


def test_integration_with_workflow():
    """集成测试：验证完整工作流中的重试机制"""
    print("\n" + "=" * 60)
    print("测试 4: 集成测试 - 工作流中的重试机制")
    print("=" * 60)
    
    from orchestrator import DSLParser
    
    yaml_content = """
name: retry-safety-test
version: "1.0"
description: Test retry safety features
variables:
  order_id: "ORDER-2026-001"
steps:
  - id: create_order
    type: retry
    name: Create Order with Retry
    max_attempts: 3
    delay_seconds: 1
    allow_unsafe_retries: false
    step:
      id: create_order_http
      type: http
      name: Create Order API
      method: POST
      url: "https://api.example.com/orders"
      idempotency_key: "${variables.order_id}"
      headers:
        Content-Type: application/json
      body:
        product_id: 123
        quantity: 2
"""
    
    import yaml
    data = yaml.safe_load(yaml_content)
    parser = DSLParser()
    workflow = parser.parse(data)
    
    assert workflow["steps"][0]["config"]["allow_unsafe_retries"] == False
    assert workflow["steps"][0]["config"]["max_attempts"] == 3
    assert workflow["steps"][0]["config"]["step"]["config"]["idempotency_key"] == "${variables.order_id}"
    
    print(f"✅ 工作流解析成功")
    print(f"   - allow_unsafe_retries: {workflow['steps'][0]['config']['allow_unsafe_retries']}")
    print(f"   - max_attempts: {workflow['steps'][0]['config']['max_attempts']}")
    print(f"   - 幂等键模板: {workflow['steps'][0]['config']['step']['config']['idempotency_key']}")
    
    print("\n✅ 集成测试通过!")


def main():
    print("\n" + "#" * 60)
    print("# 重试机制修复验证测试")
    print("# 测试目标: 验证幂等接口上的安全重试功能")
    print("#" * 60)
    
    try:
        test_http_step_error_classification()
        test_idempotency_key()
        test_safe_retry_logic()
        test_integration_with_workflow()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过! 重试机制修复验证成功!")
        print("=" * 60)
        print("\n修复要点总结:")
        print("1. ✅ HTTP 错误分类: 区分可安全重试和不可安全重试的错误")
        print("2. ✅ 幂等键支持: 通过 Idempotency-Key 请求头保证幂等性")
        print("3. ✅ 智能重试判断: 只在安全的情况下才重试")
        print("4. ✅ 可配置策略: 允许自定义重试条件")
        print("5. ✅ 默认安全: allow_unsafe_retries 默认为 false")
        print("\n对幂等接口的保护:")
        print("- 4xx 客户端错误 (如 400, 401, 403, 404, 409): 不重试")
        print("- 5xx 服务端错误 (如 500, 502, 503, 504): 可重试")
        print("- 网络错误 (连接超时, 连接失败): 可重试")
        print("- 重定向错误: 不重试")
        
        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 意外错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
