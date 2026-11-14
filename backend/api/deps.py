from fastapi import Request


def get_graph_repo(request: Request):
    return request.app.state.graph_repo


def get_groq_service(request: Request):
    return request.app.state.groq_service


def get_settings(request: Request):
    return request.app.state.settings


def get_rel_store(request: Request):
    return getattr(request.app.state, "rel_store", None)
