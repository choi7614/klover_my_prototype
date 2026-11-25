from contextlib import nullcontext

from app.ai.selection import execution_info, selected
from app.api.state import StateName, get_state


def ai_scope(request, choice=None):
    store = get_state(request, StateName.AI_SETTINGS)
    return selected(store, choice) if store is not None else nullcontext()


def execution_result(result, trace):
    return (
        result.model_copy(update={"ai_execution": execution_info()})
        if trace and trace.get("calls")
        else result
    )
