from contextlib import nullcontext

from app.ai.selection import selected


def ai_scope(request, choice=None):
    store = getattr(request.app.state, "ai_settings", None)
    return selected(store, choice) if store is not None else nullcontext()
