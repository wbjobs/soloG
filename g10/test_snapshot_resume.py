#!/usr/bin/env python3
"""
测试执行快照与断点续跑功能
"""
import sys
import os
import shutil
import tempfile
from orchestrator import DSLParser, Executor
from orchestrator.snapshot import SnapshotManager, ExecutionSnapshot


def test_snapshot_basic():
    """测试基本的快照创建和加载"""
    print("\n" + "=" * 60)
    print("测试 1: 基本快照创建与加载")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_manager = SnapshotManager(tmpdir)
        
        workflow = {
            "name": "test_workflow",
            "version": "1.0",
            "steps": [
                {"id": "step1", "type": "noop", "name": "Step 1", "depends_on": [], "config": {}},
                {"id": "step2", "type": "noop", "name": "Step 2", "depends_on": ["step1"], "config": {}}
            ],
            "variables": {}
        }
        
        snapshot = snapshot_manager.create_snapshot(
            workflow=workflow,
            execution_id="test-001",
            completed_steps={"step1"},
            failed_steps=set(),
            context={"variables": {}, "results": {"step1": {"data": "test"}}},
            logs=[{"event": "TEST"}],
            status="running"
        )
        
        assert snapshot is not None
        assert snapshot.workflow_name == "test_workflow"
        assert snapshot.execution_id == "test-001"
        assert "step1" in snapshot.completed_steps
        print("✅ 快照创建成功")
        
        loaded = snapshot_manager.load_snapshot("test_workflow", "test-001")
        assert loaded is not None
        assert loaded.execution_id == "test-001"
        assert "step1" in loaded.completed_steps
        print("✅ 快照加载成功")
        
        compatible = snapshot_manager.verify_workflow_compatible(loaded, workflow)
        assert compatible == True
        print("✅ 工作流兼容性验证通过")
        
        modified_workflow = workflow.copy()
        modified_workflow["steps"].append({"id": "step3", "type": "noop", "config": {}})
        compatible = snapshot_manager.verify_workflow_compatible(loaded, modified_workflow)
        assert compatible == False
        print("✅ 工作流修改后兼容性验证失败（正确行为）")
    
    print("\n✅ 基本快照测试通过!")


def test_executor_snapshot():
    """测试执行器中的快照功能"""
    print("\n" + "=" * 60)
    print("测试 2: 执行器快照功能")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_content = """
name: snapshot-test-workflow
version: "1.0"
description: Test snapshot functionality
variables: {}
steps:
  - id: step1
    type: noop
    name: Step 1
  - id: step2
    type: noop
    name: Step 2
    depends_on:
      - step1
  - id: step3
    type: noop
    name: Step 3
    depends_on:
      - step2
"""
        import yaml
        data = yaml.safe_load(yaml_content)
        parser = DSLParser()
        workflow = parser.parse(data)
        
        executor = Executor(
            workflow,
            use_celery=False,
            enable_snapshot=True,
            snapshot_dir=tmpdir
        )
        
        result = executor.run()
        assert result["success"] == True
        assert len(result["completed_steps"]) == 3
        print(f"✅ 工作流执行成功，完成 {len(result['completed_steps'])} 个步骤")
        
        snapshot_manager = SnapshotManager(tmpdir)
        snapshots = snapshot_manager.list_snapshots("snapshot-test-workflow")
        assert len(snapshots) == 1
        assert snapshots[0]["status"] == "completed"
        assert snapshots[0]["completed_steps"] == 3
        print(f"✅ 快照已保存，状态: {snapshots[0]['status']}")
        
        loaded = snapshot_manager.load_snapshot("snapshot-test-workflow")
        assert loaded is not None
        assert loaded.status == "completed"
        print("✅ 快照状态验证通过")
    
    print("\n✅ 执行器快照测试通过!")


def test_resume_from_snapshot():
    """测试从快照断点续跑"""
    print("\n" + "=" * 60)
    print("测试 3: 断点续跑功能")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_content = """
name: resume-test-workflow
version: "1.0"
description: Test resume from snapshot
variables: {}
steps:
  - id: step_a
    type: noop
    name: Step A
  - id: step_b
    type: noop
    name: Step B
    depends_on:
      - step_a
  - id: step_c
    type: noop
    name: Step C
    depends_on:
      - step_b
  - id: step_d
    type: noop
    name: Step D
    depends_on:
      - step_c
"""
        import yaml
        data = yaml.safe_load(yaml_content)
        parser = DSLParser()
        workflow = parser.parse(data)
        
        snapshot_manager = SnapshotManager(tmpdir)
        
        partial_snapshot = ExecutionSnapshot(
            workflow_name="resume-test-workflow",
            workflow_hash=snapshot_manager._compute_workflow_hash(workflow),
            execution_id="resume-test-001",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
            completed_steps=["step_a", "step_b"],
            failed_steps=[],
            context={"variables": {}, "results": {
                "step_a": {"message": "Completed"},
                "step_b": {"message": "Completed"}
            }},
            logs=[
                {"step_id": "step_a", "event": "COMPLETE", "status": "SUCCESS"},
                {"step_id": "step_b", "event": "COMPLETE", "status": "SUCCESS"}
            ],
            status="crashed",
            error="Simulated engine crash"
        )
        
        import json
        from dataclasses import asdict
        snapshot_path = os.path.join(tmpdir, "resume-test-workflow_resume-test-001.json")
        with open(snapshot_path, "w") as f:
            json.dump(asdict(partial_snapshot), f, default=str)
        print("✅ 创建了模拟崩溃的快照（已完成 step_a 和 step_b）")
        
        executor = Executor(
            workflow,
            use_celery=False,
            enable_snapshot=True,
            snapshot_dir=tmpdir
        )
        
        snapshot = snapshot_manager.load_snapshot("resume-test-workflow", "resume-test-001")
        assert snapshot is not None
        
        resumed = executor.resume_from_snapshot(snapshot)
        assert resumed == True
        print("✅ 从快照恢复成功")
        assert "step_a" in executor.completed_steps
        assert "step_b" in executor.completed_steps
        print(f"✅ 已恢复 {len(executor.completed_steps)} 个已完成步骤")
        
        result = executor.run()
        assert result["success"] == True
        assert result["resumed_from_snapshot"] == True
        print("✅ 断点续跑执行成功")
        
        all_steps = {"step_a", "step_b", "step_c", "step_d"}
        assert set(result["completed_steps"]) == all_steps
        print(f"✅ 所有步骤均已完成: {', '.join(result['completed_steps'])}")
        
        assert "step_a" in executor.context["results"]
        assert "step_b" in executor.context["results"]
        assert "step_c" in executor.context["results"]
        assert "step_d" in executor.context["results"]
        print("✅ 所有步骤的执行结果都已保存")
    
    print("\n✅ 断点续跑测试通过!")


def test_snapshot_skip_completed_steps():
    """测试续跑时跳过已完成的步骤"""
    print("\n" + "=" * 60)
    print("测试 4: 续跑时跳过已完成步骤")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_content = """
name: skip-test-workflow
version: "1.0"
description: Test skipping completed steps
variables: {}
steps:
  - id: first
    type: noop
    name: First Step
  - id: second
    type: noop
    name: Second Step
    depends_on:
      - first
"""
        import yaml
        data = yaml.safe_load(yaml_content)
        parser = DSLParser()
        workflow = parser.parse(data)
        
        execution_counter = {"first": 0, "second": 0}
        
        original_init = __import__('orchestrator.steps.noop_step', fromlist=['NoopStep']).NoopStep.execute
        
        def counting_execute(self, context, logger):
            execution_counter[self.id] += 1
            logger.logger.info(f"Executing step: {self.id} (count: {execution_counter[self.id]})")
            return original_init(self, context, logger)
        
        with patch('orchestrator.steps.noop_step.NoopStep.execute', counting_execute):
            executor = Executor(
                workflow,
                use_celery=False,
                enable_snapshot=True,
                snapshot_dir=tmpdir
            )
            
            result = executor.run()
            assert result["success"] == True
            assert execution_counter["first"] == 1
            assert execution_counter["second"] == 1
            print("✅ 首次执行：每个步骤执行 1 次")
            
            snapshot_manager = SnapshotManager(tmpdir)
            snapshot = snapshot_manager.load_snapshot("skip-test-workflow")
            
            executor2 = Executor(
                workflow,
                use_celery=False,
                enable_snapshot=True,
                snapshot_dir=tmpdir
            )
            executor2.resume_from_snapshot(snapshot)
            
            execution_counter["first"] = 0
            execution_counter["second"] = 0
            
            result2 = executor2.run()
            assert result2["success"] == True
            assert execution_counter["first"] == 0
            assert execution_counter["second"] == 0
            print("✅ 续跑执行：已完成的步骤被跳过，执行次数为 0")
    
    print("\n✅ 跳过已完成步骤测试通过!")


def test_snapshot_management():
    """测试快照管理功能（列出、删除）"""
    print("\n" + "=" * 60)
    print("测试 5: 快照管理功能")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_manager = SnapshotManager(tmpdir)
        
        workflow = {
            "name": "mgmt-test",
            "version": "1.0",
            "steps": [],
            "variables": {}
        }
        
        for i in range(3):
            snapshot_manager.create_snapshot(
                workflow=workflow,
                execution_id=f"exec-{i}",
                completed_steps=set(),
                failed_steps=set(),
                context={},
                logs=[],
                status="completed"
            )
        
        snapshots = snapshot_manager.list_snapshots("mgmt-test")
        assert len(snapshots) == 3
        print(f"✅ 列出了 {len(snapshots)} 个快照")
        
        deleted = snapshot_manager.delete_snapshot("mgmt-test", "exec-1")
        assert deleted == True
        snapshots = snapshot_manager.list_snapshots("mgmt-test")
        assert len(snapshots) == 2
        print("✅ 删除单个快照成功")
        
        count = snapshot_manager.delete_all_snapshots("mgmt-test")
        assert count == 2
        snapshots = snapshot_manager.list_snapshots("mgmt-test")
        assert len(snapshots) == 0
        print("✅ 批量删除快照成功")
    
    print("\n✅ 快照管理测试通过!")


def test_workflow_hash_compatibility():
    """测试工作流变更后的兼容性检查"""
    print("\n" + "=" * 60)
    print("测试 6: 工作流变更兼容性检查")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        original_workflow = {
            "name": "compat-test",
            "version": "1.0",
            "steps": [
                {"id": "step1", "type": "noop", "config": {}},
                {"id": "step2", "type": "noop", "depends_on": ["step1"], "config": {}}
            ],
            "variables": {}
        }
        
        snapshot_manager = SnapshotManager(tmpdir)
        snapshot = snapshot_manager.create_snapshot(
            workflow=original_workflow,
            execution_id="compat-001",
            completed_steps={"step1"},
            failed_steps=set(),
            context={},
            logs=[],
            status="crashed"
        )
        
        workflow_same = {
            "name": "compat-test",
            "version": "1.0",
            "steps": [
                {"id": "step1", "type": "noop", "config": {}},
                {"id": "step2", "type": "noop", "depends_on": ["step1"], "config": {}}
            ],
            "variables": {"new_var": "test"}
        }
        assert snapshot_manager.verify_workflow_compatible(snapshot, workflow_same) == True
        print("✅ 变量变更不影响兼容性（正确）")
        
        workflow_modified = {
            "name": "compat-test",
            "version": "1.0",
            "steps": [
                {"id": "step1", "type": "noop", "config": {}},
                {"id": "step2", "type": "http", "depends_on": ["step1"], "config": {"url": "http://example.com"}},
                {"id": "step3", "type": "noop", "depends_on": ["step2"], "config": {}}
            ],
            "variables": {}
        }
        assert snapshot_manager.verify_workflow_compatible(snapshot, workflow_modified) == False
        print("✅ 步骤变更导致不兼容（正确）")
        
        workflow_renamed = {
            "name": "compat-test-modified",
            "version": "1.0",
            "steps": original_workflow["steps"],
            "variables": {}
        }
        assert snapshot_manager.verify_workflow_compatible(snapshot, workflow_renamed) == False
        print("✅ 工作流名称变更导致不兼容（正确）")
    
    print("\n✅ 工作流兼容性测试通过!")


def main():
    print("\n" + "#" * 60)
    print("# 执行快照与断点续跑功能测试")
    print("#" * 60)
    
    try:
        test_snapshot_basic()
        test_executor_snapshot()
        test_resume_from_snapshot()
        test_snapshot_skip_completed_steps()
        test_snapshot_management()
        test_workflow_hash_compatibility()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过! 快照与断点续跑功能验证成功!")
        print("=" * 60)
        print("\n功能总结:")
        print("1. ✅ 自动快照: 每个步骤完成后自动保存执行状态")
        print("2. ✅ 断点续跑: 从最近成功的步骤继续执行")
        print("3. ✅ 跳过已完成步骤: 避免重复执行已完成的步骤")
        print("4. ✅ 工作流兼容性检查: 防止工作流变更后错误续跑")
        print("5. ✅ 快照管理: 支持列出、删除、清理快照")
        print("6. ✅ 崩溃恢复: 引擎崩溃后可从快照恢复")
        print("\n使用示例:")
        print("  # 启用快照执行")
        print("  python main.py workflow.yaml --enable-snapshot")
        print("  # 从最近快照续跑")
        print("  python main.py workflow.yaml --resume")
        print("  # 从指定快照续跑")
        print("  python main.py workflow.yaml --resume-from <execution_id>")
        print("  # 列出所有快照")
        print("  python main.py workflow.yaml --list-snapshots")
        print("  # 清理快照")
        print("  python main.py workflow.yaml --clean-snapshots")
        
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
    from unittest.mock import patch
    sys.exit(main())
