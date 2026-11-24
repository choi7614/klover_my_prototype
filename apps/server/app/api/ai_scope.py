from contextlib import nullcontext

from app.ai.selection import execution_info, selected


def ai_scope(request, choice=None):
    store = getattr(request.app.state, "ai_settings", None)
    return selected(store, choice) if store is not None else nullcontext()


def execution_result(result, trace):
    return (
        result.model_copy(update={"ai_execution": execution_info()})
        if trace and trace.get("calls")
        else result
    )
