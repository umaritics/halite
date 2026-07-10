from abc import ABC, abstractmethod


class BaseAgent(ABC):
    def __init__(self, graph_repo, groq_service=None):
        self.graph_repo = graph_repo
        self.groq_service = groq_service

    @abstractmethod
    def run(self, payload: dict) -> dict:
        pass
