"""
Autonomous Learning Loop — when the AI Human is idle for more than idle_threshold
seconds, it automatically researches its own knowledge gaps, reads documentation,
explores new tools, and stores learnings in ChromaDB.

Learning activities:
1. Identify knowledge gaps (ask LLM what it doesn't know well)
2. Web search for those topics
3. Read and summarize found articles
4. Store summaries in semantic memory
5. Identify patterns in past failures and learn from them
6. Explore system capabilities not yet used
7. Generate practice tasks to improve skills
"""

from __future__ import annotations
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from utils.logger import get_logger

log = get_logger(__name__)


class AutonomousLearningLoop:
    """
    Background thread that researches knowledge gaps during agent idle time.
    """

    def __init__(
        self,
        llm_generate_fn: Callable,
        semantic_memory=None,
        episodic_memory=None,
        web_search_fn: Optional[Callable] = None,
        idle_threshold: int = 300,  # 5 minutes idle before learning starts
        session_duration: int = 1800,  # max 30 min learning per session
    ):
        self._llm = llm_generate_fn
        self._semantic = semantic_memory
        self._episodic = episodic_memory
        self._web_search = web_search_fn
        self._idle_threshold = idle_threshold
        self._session_duration = session_duration
        self._last_activity: float = time.time()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._currently_learning = False
        self._topics_learned: list[str] = []
        self._log_path = Path("data/learning_log.jsonl")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Autonomous learning loop started")

    def stop(self) -> None:
        self._running = False
        log.info("Autonomous learning loop stopped")

    def notify_activity(self) -> None:
        """Call this whenever the agent does something to reset idle timer."""
        self._last_activity = time.time()
        if self._currently_learning:
            log.info("Activity detected — pausing learning session")

    @property
    def is_learning(self) -> bool:
        return self._currently_learning

    def get_learned_topics(self) -> list[str]:
        return list(self._topics_learned)

    # ── Main Loop ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            idle_time = time.time() - self._last_activity
            if idle_time >= self._idle_threshold and not self._currently_learning:
                log.info(f"Agent idle for {idle_time:.0f}s — starting learning session")
                self._run_learning_session()
            time.sleep(30)  # check every 30 seconds

    def _run_learning_session(self) -> None:
        self._currently_learning = True
        session_start = time.time()
        session_log = {
            "session_start": datetime.now().isoformat(),
            "activities": [],
        }

        try:
            # 1. Identify knowledge gaps
            gaps = self._identify_knowledge_gaps()
            if not gaps:
                return

            log.info(f"Knowledge gaps identified: {gaps[:3]}")

            for topic in gaps[:5]:  # research up to 5 topics
                if not self._running:
                    break
                if time.time() - session_start > self._session_duration:
                    log.info("Learning session time limit reached")
                    break
                if time.time() - self._last_activity < self._idle_threshold:
                    log.info("Agent became active — stopping learning")
                    break

                log.info(f"Researching: {topic}")
                learned = self._research_topic(topic)
                if learned:
                    self._topics_learned.append(topic)
                    session_log["activities"].append({"topic": topic, "learned": learned[:200]})

            # 2. Learn from past failures
            failure_learnings = self._learn_from_failures()
            if failure_learnings:
                session_log["activities"].append({"type": "failure_analysis", "learned": failure_learnings})

            # 3. Explore unused tools
            tool_knowledge = self._explore_capabilities()
            if tool_knowledge:
                session_log["activities"].append({"type": "capability_exploration", "learned": tool_knowledge})

        except Exception as e:
            log.error(f"Learning session error: {e}")
        finally:
            self._currently_learning = False
            session_log["session_end"] = datetime.now().isoformat()
            session_log["duration_seconds"] = round(time.time() - session_start, 1)
            self._save_session_log(session_log)
            topics_count = len(session_log["activities"])
            log.info(f"Learning session complete — {topics_count} activities in {session_log['duration_seconds']}s")

    def _identify_knowledge_gaps(self) -> list[str]:
        """Ask the LLM to identify what it should learn more about."""
        try:
            # Pull recent failures from memory
            failures_context = ""
            if self._episodic:
                failures = self._episodic.recall_failures("task failed error")
                if failures:
                    failures_context = f"\nRecent failures: {'; '.join(f['content'][:100] for f in failures[:5])}"

            prompt = (
                "You are an AI agent identifying your own knowledge gaps.\n"
                "Based on your role as an autonomous computer-operating agent, "
                "what topics would be most valuable to research right now?\n"
                f"{failures_context}\n"
                "List 5-8 specific, searchable topics as a JSON array of strings.\n"
                "Focus on: programming patterns, automation techniques, error handling, "
                "tools and libraries, OS internals, web technologies.\n"
                "Example: [\"Python asyncio best practices\", \"Windows API for process management\"]\n"
                "Return ONLY the JSON array."
            )
            response = self._llm([{"role": "user", "content": prompt}])
            # Extract JSON array
            import re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            log.debug(f"Gap identification failed: {e}")
        return ["Python automation best practices", "Windows task automation", "Error handling patterns"]

    def _research_topic(self, topic: str) -> Optional[str]:
        """Research a topic and store learnings in memory."""
        try:
            content = ""

            # Web search if available
            if self._web_search:
                try:
                    search_results = self._web_search(topic)
                    if search_results and not isinstance(search_results, dict):
                        content = str(search_results)[:3000]
                except Exception:
                    pass

            # If no web search, ask LLM to recall what it knows
            if not content:
                prompt = (
                    f"Provide a comprehensive technical summary of: {topic}\n"
                    "Include: key concepts, best practices, common pitfalls, code examples.\n"
                    "Keep it concise but complete (200-400 words)."
                )
                content = self._llm([{"role": "user", "content": prompt}])

            if not content:
                return None

            # Summarize and extract key facts
            summary_prompt = (
                f"Extract 3-5 key actionable facts/techniques about '{topic}' from this text.\n"
                f"Format as a JSON array of strings. Each fact should be practical and specific.\n\n"
                f"Text:\n{content[:2000]}\n\nReturn ONLY the JSON array."
            )
            summary_response = self._llm([{"role": "user", "content": summary_prompt}])

            import re
            facts = []
            match = re.search(r'\[.*?\]', summary_response, re.DOTALL)
            if match:
                facts = json.loads(match.group())

            # Store in semantic memory
            if self._semantic and facts:
                for fact in facts:
                    self._semantic.store(
                        f"[LEARNED: {topic}] {fact}",
                        source=f"auto_learned:{topic}",
                        tags=["auto_learned"],
                    )

            return f"Learned {len(facts)} facts about '{topic}'"
        except Exception as e:
            log.debug(f"Research failed for '{topic}': {e}")
            return None

    def _learn_from_failures(self) -> Optional[str]:
        """Analyze past failures and extract learnings."""
        if not self._episodic:
            return None
        try:
            failures = self._episodic.recall_failures("error failed exception")
            if not failures:
                return None

            failure_text = "\n".join(f.get("content", "")[:200] for f in failures[:10])
            prompt = (
                f"Analyze these past failures and identify:\n"
                f"1. Common patterns\n"
                f"2. Root causes\n"
                f"3. Prevention strategies\n\n"
                f"Failures:\n{failure_text}\n\n"
                f"Provide 3 specific lessons as a JSON array of strings.\n"
                f"Return ONLY the JSON array."
            )
            response = self._llm([{"role": "user", "content": prompt}])

            import re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                lessons = json.loads(match.group())
                if self._semantic:
                    for lesson in lessons:
                        self._semantic.store(
                            f"[FAILURE LESSON] {lesson}",
                            source="failure_analysis",
                            tags=["failure_lesson"],
                        )
                return f"Extracted {len(lessons)} lessons from past failures"
        except Exception as e:
            log.debug(f"Failure learning failed: {e}")
        return None

    def _explore_capabilities(self) -> Optional[str]:
        """Discover and document agent capabilities not yet well understood."""
        try:
            prompt = (
                "You are an AI agent exploring your own capabilities.\n"
                "Generate 3 practice tasks that would help you improve at:\n"
                "- File system operations\n"
                "- Web interaction\n"
                "- Code execution and debugging\n\n"
                "Format as JSON array of task descriptions.\n"
                "Return ONLY the JSON array."
            )
            response = self._llm([{"role": "user", "content": prompt}])

            import re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                tasks = json.loads(match.group())
                if self._semantic:
                    self._semantic.store(
                        f"[PRACTICE TASKS] {'; '.join(tasks)}",
                        source="capability_exploration",
                        tags=["practice_tasks"],
                    )
                return f"Generated {len(tasks)} practice tasks"
        except Exception as e:
            log.debug(f"Capability exploration failed: {e}")
        return None

    def _save_session_log(self, session_log: dict) -> None:
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(session_log) + "\n")
        except Exception:
            pass

    def get_learning_summary(self) -> str:
        """Summary of all autonomous learning for agent to include in context."""
        if not self._log_path.exists():
            return "No autonomous learning sessions yet"

        sessions = []
        try:
            with open(self._log_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        sessions.append(json.loads(line.strip()))
                    except Exception:
                        pass
        except Exception:
            return "Error reading learning log"

        if not sessions:
            return "No learning sessions recorded"

        total_activities = sum(len(s.get("activities", [])) for s in sessions)
        return (
            f"Autonomous learning: {len(sessions)} sessions, "
            f"{total_activities} topics researched, "
            f"topics: {', '.join(self._topics_learned[-5:])}"
        )
