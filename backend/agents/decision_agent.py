import uuid

from agents.base_agent import BaseAgent


class DecisionAgent(BaseAgent):
    def run(self, payload: dict) -> dict:
        decision = self.graph_repo.create_decision(
            {
                "id": str(uuid.uuid4()),
                "title": payload["title"],
                "reasoning": payload["reasoning"],
                "status": "active",
                "source": "manual",
                "source_ref": "manual",
                "created_by": payload.get("created_by", "user"),
            }
        )

        for name in payload.get("related_component_names", []):
            component = self.graph_repo.find_or_create_component_by_name(name)
            self.graph_repo.link_decision_about(decision["id"], component["id"])

        for ticket_id in payload.get("linked_ticket_ids", []):
            self.graph_repo.link_decision_ticket(decision["id"], str(ticket_id))

        return self.graph_repo.get_decision(decision["id"])
