from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import NotRequired, Annotated
from typing import Literal
from typing_extensions import TypedDict


class Todo(TypedDict):
    """Todo to track."""

    content: str
    status: Literal["pending", "in_progress", "completed"]


def file_reducer(l, r):
    if l is None:
        return r
    elif r is None:
        return l
    else:
        return {**l, **r}


def todo_reducer(left, right):
    """Merge todo lists from concurrent updates, handling conflicts intelligently.
    
    When multiple agents update todos in parallel, this reducer ensures proper merging:
    - Preserves all unique todos from both lists
    - For duplicate todos (same content), uses status priority: completed > in_progress > pending
    - Maintains order of todos
    """
    if left is None:
        return right
    elif right is None:
        return left
    else:
        # Use content as key, intelligently merge status updates
        todo_dict = {}
        
        # First, add all todos from left
        for todo in left:
            todo_dict[todo['content']] = todo
        
        # Then merge todos from right with conflict resolution
        for todo in right:
            if todo['content'] in todo_dict:
                # Status priority: completed > in_progress > pending
                existing = todo_dict[todo['content']]
                status_priority = {'completed': 3, 'in_progress': 2, 'pending': 1}
                
                # Use the todo with higher priority status
                if status_priority.get(todo['status'], 0) > status_priority.get(existing['status'], 0):
                    todo_dict[todo['content']] = todo
            else:
                # New todo, add it
                todo_dict[todo['content']] = todo
        
        # Return as list maintaining insertion order
        return list(todo_dict.values())


class DeepAgentState(AgentState):
    todos: Annotated[NotRequired[list[Todo]], todo_reducer]
    files: Annotated[NotRequired[dict[str, str]], file_reducer]
