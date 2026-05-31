#!/usr/bin/env python3
import argparse
import sys
import json
from orchestrator import DSLParser, Executor
from orchestrator.snapshot import SnapshotManager


def main():
    parser = argparse.ArgumentParser(description="Orchestration Engine - Execute YAML-defined workflows")
    parser.add_argument("workflow_file", nargs="?", help="Path to the YAML workflow file")
    parser.add_argument("--no-celery", action="store_true", help="Run without Celery (synchronous mode)")
    parser.add_argument("--validate-only", action="store_true", help="Only validate the workflow, don't execute")
    parser.add_argument("--output", help="Path to write execution logs as JSON")
    
    snapshot_group = parser.add_argument_group("Snapshot & Resume Options")
    snapshot_group.add_argument("--enable-snapshot", action="store_true", 
                                help="Enable execution snapshots for crash recovery")
    snapshot_group.add_argument("--snapshot-dir", default=".snapshots", 
                                help="Directory to store snapshots (default: .snapshots)")
    snapshot_group.add_argument("--resume", action="store_true", 
                                help="Resume from the latest snapshot")
    snapshot_group.add_argument("--resume-from", metavar="EXECUTION_ID", 
                                help="Resume from a specific execution ID")
    snapshot_group.add_argument("--resume-from-file", metavar="SNAPSHOT_FILE", 
                                help="Resume from a specific snapshot file")
    snapshot_group.add_argument("--list-snapshots", action="store_true", 
                                help="List all available snapshots")
    snapshot_group.add_argument("--clean-snapshots", action="store_true", 
                                help="Delete all snapshots for the workflow")
    snapshot_group.add_argument("--delete-snapshot", metavar="EXECUTION_ID", 
                                help="Delete a specific snapshot")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("ORCHESTRATION ENGINE")
    print("=" * 80)
    
    try:
        if args.list_snapshots:
            _list_snapshots(args.workflow_file, args.snapshot_dir)
            return
        
        if args.clean_snapshots:
            _clean_snapshots(args.workflow_file, args.snapshot_dir)
            return
        
        if args.delete_snapshot:
            _delete_snapshot(args.workflow_file, args.delete_snapshot, args.snapshot_dir)
            return
        
        if not args.workflow_file:
            parser.print_help()
            print("\n❌ Error: workflow_file is required for execution")
            sys.exit(1)
        
        print(f"\n📄 Parsing workflow: {args.workflow_file}")
        dsl_parser = DSLParser()
        workflow = dsl_parser.parse_file(args.workflow_file)
        
        print(f"✅ Workflow loaded: {workflow['name']} (v{workflow['version']})")
        print(f"📝 Description: {workflow['description']}")
        print(f"🔢 Steps defined: {len(workflow['steps'])}")
        
        if args.validate_only:
            print("\n🔍 Validating workflow...")
            executor = Executor(workflow, use_celery=not args.no_celery)
            if executor.validate():
                print("✅ Workflow is valid! DAG has no cycles.")
                
                print("\n📊 Execution order (topological sort):")
                order = executor.dag.topological_sort()
                for i, step_id in enumerate(order, 1):
                    step = executor.dag.get_step(step_id)
                    deps = step.get("depends_on", [])
                    dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
                    print(f"  {i}. {step_id} [{step['type']}]{dep_str}")
            else:
                print("❌ Workflow validation failed!")
                sys.exit(1)
            return
        
        enable_snapshot = args.enable_snapshot or args.resume or args.resume_from or args.resume_from_file
        
        print(f"\n🚀 Starting execution{' (synchronous mode)' if args.no_celery else ' (Celery mode)'}...")
        if enable_snapshot:
            print(f"💾 Snapshot enabled, directory: {args.snapshot_dir}")
        print()
        
        executor = Executor(
            workflow, 
            use_celery=not args.no_celery,
            enable_snapshot=enable_snapshot,
            snapshot_dir=args.snapshot_dir
        )
        
        if args.resume or args.resume_from or args.resume_from_file:
            snapshot_manager = SnapshotManager(args.snapshot_dir)
            
            if args.resume_from_file:
                print(f"🔄 Loading snapshot from file: {args.resume_from_file}")
                snapshot = snapshot_manager.load_snapshot_by_file(args.resume_from_file)
            elif args.resume_from:
                print(f"🔄 Loading snapshot for execution: {args.resume_from}")
                snapshot = snapshot_manager.load_snapshot(workflow["name"], args.resume_from)
            else:
                print(f"🔄 Loading latest snapshot for workflow: {workflow['name']}")
                snapshot = snapshot_manager.load_snapshot(workflow["name"])
            
            if not snapshot:
                print("❌ No snapshot found to resume from")
                sys.exit(1)
            
            if not executor.resume_from_snapshot(snapshot):
                print("❌ Failed to resume from snapshot")
                sys.exit(1)
            
            print(f"✅ Resumed from snapshot: {snapshot.execution_id}")
            print(f"   Status: {snapshot.status}")
            print(f"   Completed steps: {len(snapshot.completed_steps)}")
            if snapshot.error:
                print(f"   Previous error: {snapshot.error}")
        
        result = executor.run()
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str, ensure_ascii=False)
            print(f"\n💾 Execution logs written to: {args.output}")
        
        print("\n" + "=" * 80)
        if result.get("resumed_from_snapshot"):
            print(f"🔄 Execution resumed from snapshot: {result.get('execution_id')}")
        if result["success"]:
            print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            print(f"📊 Completed steps: {len(result['completed_steps'])}")
            print(f"❌ Failed steps: {len(result['failed_steps'])}")
        else:
            print("❌ WORKFLOW FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"📊 Completed steps: {len(result.get('completed_steps', []))}")
            print(f"❌ Failed steps: {', '.join(result.get('failed_steps', []))}")
            if enable_snapshot:
                print(f"\n💾 Snapshot saved with execution_id: {result.get('execution_id')}")
                print(f"   To resume, run: python main.py {args.workflow_file} --resume")
        print("=" * 80)
        
        sys.exit(0 if result["success"] else 1)
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _list_snapshots(workflow_file: str, snapshot_dir: str):
    snapshot_manager = SnapshotManager(snapshot_dir)
    
    if workflow_file:
        dsl_parser = DSLParser()
        workflow = dsl_parser.parse_file(workflow_file)
        workflow_name = workflow["name"]
        print(f"\n📋 Snapshots for workflow: {workflow_name}")
        snapshots = snapshot_manager.list_snapshots(workflow_name)
    else:
        print("\n📋 All snapshots:")
        snapshots = snapshot_manager.list_snapshots()
    
    if not snapshots:
        print("   No snapshots found")
        return
    
    print(f"   Found {len(snapshots)} snapshot(s):\n")
    for i, snap in enumerate(snapshots, 1):
        status_icon = {
            "running": "⏳",
            "completed": "✅",
            "failed": "❌",
            "crashed": "💥"
        }.get(snap["status"], "•")
        
        print(f"   {i}. {status_icon} [{snap['updated_at']}]")
        print(f"      Workflow: {snap['workflow_name']}")
        print(f"      Execution ID: {snap['execution_id']}")
        print(f"      Status: {snap['status']}")
        print(f"      Completed: {snap['completed_steps']} steps")
        print(f"      Failed: {snap['failed_steps']} steps")
        print()


def _clean_snapshots(workflow_file: str, snapshot_dir: str):
    snapshot_manager = SnapshotManager(snapshot_dir)
    
    if workflow_file:
        dsl_parser = DSLParser()
        workflow = dsl_parser.parse_file(workflow_file)
        workflow_name = workflow["name"]
        count = snapshot_manager.delete_all_snapshots(workflow_name)
        print(f"\n🗑️  Deleted {count} snapshot(s) for workflow: {workflow_name}")
    else:
        count = snapshot_manager.delete_all_snapshots()
        print(f"\n🗑️  Deleted {count} snapshot(s) in total")


def _delete_snapshot(workflow_file: str, execution_id: str, snapshot_dir: str):
    snapshot_manager = SnapshotManager(snapshot_dir)
    
    if workflow_file:
        dsl_parser = DSLParser()
        workflow = dsl_parser.parse_file(workflow_file)
        workflow_name = workflow["name"]
        deleted = snapshot_manager.delete_snapshot(workflow_name, execution_id)
    else:
        deleted = False
        for snap in snapshot_manager.list_snapshots():
            if snap["execution_id"] == execution_id:
                deleted = snapshot_manager.delete_snapshot(snap["workflow_name"], execution_id)
                break
    
    if deleted:
        print(f"\n🗑️  Deleted snapshot: {execution_id}")
    else:
        print(f"\n❌ Snapshot not found: {execution_id}")


if __name__ == "__main__":
    main()
