"""
AgentWiring — centralizes optional subsystem attachment to AgentOrchestrator.

Replaces scattered `agent._foo = bar` lines in main.py with a clean public
interface. Each method calls agent.attach() and returns self for chaining.

Usage:
    wiring = AgentWiring(agent)
    wiring.attach_dashboard(dashboard)
    wiring.attach_recorder(recorder)
    wiring.attach_converter(converter)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.agent import AgentOrchestrator


class AgentWiring:
    """Builder that attaches optional subsystems to the agent."""

    def __init__(self, agent: AgentOrchestrator):
        self._agent = agent

    def attach_dashboard(self, dashboard) -> AgentWiring:
        self._agent.attach("dashboard", dashboard)
        return self

    def attach_docs(self, docs) -> AgentWiring:
        self._agent.attach("docs", docs)
        return self

    def attach_multi_agent(self, multi_agent) -> AgentWiring:
        self._agent.attach("multi_agent", multi_agent)
        return self

    def attach_recorder(self, recorder) -> AgentWiring:
        self._agent.attach("recorder", recorder)
        return self

    def attach_converter(self, converter) -> AgentWiring:
        self._agent.attach("converter", converter)
        return self

    def attach_screen_recorder(self, screen_recorder) -> AgentWiring:
        self._agent.attach("screen_recorder", screen_recorder)
        return self

    def attach_templates(self, templates) -> AgentWiring:
        self._agent.attach("templates", templates)
        return self

    def attach_lang_support(self, lang_support) -> AgentWiring:
        self._agent.attach("lang_support", lang_support)
        return self

    def attach_learning_loop(self, learning_loop) -> AgentWiring:
        self._agent.attach("learning_loop", learning_loop)
        return self

    def attach_stress_detector(self, stress_detector) -> AgentWiring:
        self._agent.attach("stress_detector", stress_detector)
        return self

    def attach_mobile_bridge(self, mobile_bridge) -> AgentWiring:
        self._agent.attach("mobile_bridge", mobile_bridge)
        return self

    def attach_peer_network(self, peer_network) -> AgentWiring:
        self._agent.attach("peer_network", peer_network)
        return self

    def attach_browser_bridge(self, browser_bridge) -> AgentWiring:
        self._agent.attach("browser_bridge", browser_bridge)
        return self
