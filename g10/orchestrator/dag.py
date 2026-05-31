from typing import Dict, List, Any, Set
from collections import deque


class DAG:
    def __init__(self, steps: List[Dict[str, Any]]):
        self.steps = steps
        self.step_map = {step["id"]: step for step in steps}
        self.adjacency_list = {}
        self.in_degree = {}
        self._build_graph()

    def _build_graph(self):
        for step in self.steps:
            step_id = step["id"]
            if step_id not in self.adjacency_list:
                self.adjacency_list[step_id] = []
            if step_id not in self.in_degree:
                self.in_degree[step_id] = 0
            
            for dep in step.get("depends_on", []):
                if dep not in self.step_map:
                    raise ValueError(f"Step '{step_id}' depends on unknown step '{dep}'")
                
                if dep not in self.adjacency_list:
                    self.adjacency_list[dep] = []
                self.adjacency_list[dep].append(step_id)
                self.in_degree[step_id] = self.in_degree.get(step_id, 0) + 1

    def topological_sort(self) -> List[str]:
        in_degree_copy = self.in_degree.copy()
        queue = deque()
        
        for step_id, degree in in_degree_copy.items():
            if degree == 0:
                queue.append(step_id)
        
        result = []
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in self.adjacency_list.get(current, []):
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(self.steps):
            raise ValueError("Graph contains a cycle - cannot perform topological sort")
        
        return result

    def get_ready_steps(self, completed_steps: Set[str]) -> List[str]:
        ready = []
        for step_id in self.step_map:
            if step_id in completed_steps:
                continue
            
            deps = self.step_map[step_id].get("depends_on", [])
            if all(dep in completed_steps for dep in deps):
                ready.append(step_id)
        
        return ready

    def get_step(self, step_id: str) -> Dict[str, Any]:
        return self.step_map.get(step_id)

    def get_dependents(self, step_id: str) -> List[str]:
        return self.adjacency_list.get(step_id, [])

    def get_dependencies(self, step_id: str) -> List[str]:
        return self.step_map.get(step_id, {}).get("depends_on", [])

    def validate(self) -> bool:
        try:
            self.topological_sort()
            return True
        except ValueError:
            return False
