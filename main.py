"""
AI Human — Entry Point

Usage:
  python launcher.py              ← RECOMMENDED (watchdog + auto-restart)
  python main.py                  ← direct run
  python main.py --no-ui          ← headless terminal mode
  python main.py --check          ← hardware report
  python main.py --goal "..."     ← set initial goal
  python main.py --no-proactive   ← disable background watching
  python main.py --no-remote      ← disable web control panel
  python main.py --no-mobile      ← disable mobile companion server
  python main.py --no-wake-word   ← disable wake word detection
  python main.py --no-learning    ← disable autonomous learning loop
  python main.py --no-stress      ← disable stress detection
  python main.py --no-peers       ← disable peer network
  python main.py --no-recording   ← disable screen recording
  python main.py --remote-port 8080
  python main.py --mobile-port 8081
  python main.py --peer-port 8090
  python main.py --vault-pass "..."  ← unlock credential vault
  python main.py --lang fr           ← set UI language
  python main.py --wake-word "hey computer"
"""

from __future__ import annotations

import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="AI Human — Autonomous AI Agent")
    parser.add_argument("--no-ui",          action="store_true")
    parser.add_argument("--check",          action="store_true")
    parser.add_argument("--goal",           type=str, default="")
    parser.add_argument("--no-proactive",   action="store_true")
    parser.add_argument("--no-remote",      action="store_true")
    parser.add_argument("--no-mobile",      action="store_true")
    parser.add_argument("--no-monitor",     action="store_true")
    parser.add_argument("--no-wake-word",   action="store_true")
    parser.add_argument("--no-learning",    action="store_true")
    parser.add_argument("--no-stress",      action="store_true")
    parser.add_argument("--no-peers",       action="store_true")
    parser.add_argument("--no-recording",   action="store_true")
    parser.add_argument("--remote-port",    type=int, default=8080)
    parser.add_argument("--mobile-port",    type=int, default=8081)
    parser.add_argument("--peer-port",      type=int, default=8090)
    # NOTE: --vault-pass intentionally removed for security.
    # Passphrases passed as CLI args appear in process list and shell history.
    # Use the AI_HUMAN_VAULT_PASS environment variable instead.
    parser.add_argument("--lang",           type=str, default="")
    parser.add_argument("--wake-word",      type=str, default="hey ai")
    args = parser.parse_args()

    # Hardware check mode
    if args.check:
        from utils.hardware import print_hardware_report
        print_hardware_report()
        return

    # ── Credential vault ──────────────────────────────────────────────────────
    # SECURITY: only read vault passphrase from env, never from CLI args
    vault_pass = os.environ.get("AI_HUMAN_VAULT_PASS", "")
    if vault_pass:
        try:
            from core.credential_manager import get_vault
            get_vault().unlock(vault_pass)
            get_vault().inject_to_env()
            print("  Vault: unlocked and injected to env")
        except Exception as e:
            print(f"  Vault: failed to unlock — {e}")

    # ── Config ────────────────────────────────────────────────────────────────
    from config import get_config
    config = get_config()

    print("\n🤖 AI Human starting...")
    print(f"  Provider : {config.llm_provider}")
    print(f"  Model    : {config.llm_model or '(auto-detect)'}")

    # ── LLM ───────────────────────────────────────────────────────────────────
    from llm.factory import create_llm
    print("  Loading LLM...")
    llm = create_llm(config, model_type="text")
    print(f"  LLM ready: {llm.model_name}")

    vision_llm = None
    if llm.supports_vision():
        vision_llm = llm
    elif config.vision_model:
        try:
            vision_llm = create_llm(config, model_type="vision")
        except Exception:
            pass

    # ── Event bus ─────────────────────────────────────────────────────────────
    from core.event_bus import EventBus
    bus = EventBus()

    # ── Performance Dashboard ─────────────────────────────────────────────────
    from core.performance_dashboard import PerformanceDashboard
    dashboard = PerformanceDashboard()

    # ── Auto-Documentation ────────────────────────────────────────────────────
    from core.auto_documentation import AutoDocumentation
    docs = AutoDocumentation()
    docs.start()

    # ── Agent ─────────────────────────────────────────────────────────────────
    from core.agent import AgentOrchestrator
    from core.wiring import AgentWiring
    agent = AgentOrchestrator(config, llm, vision_llm, bus)
    wiring = AgentWiring(agent)

    # Attach dashboard + docs
    wiring.attach_dashboard(dashboard)
    wiring.attach_docs(docs)

    # ── Goal Persistence ──────────────────────────────────────────────────────
    from core.goal_persistence import GoalPersistence
    persistence = GoalPersistence()
    saved = persistence.load()
    if saved and not args.goal:
        print(f"  Resuming goal: {saved['goal'][:60]}")
        agent.set_goal(saved["goal"])
        if saved.get("context_window"):
            agent.context_window = saved["context_window"]

    # ── Natural Language Scheduler ────────────────────────────────────────────
    from core.scheduler import Scheduler
    scheduler = Scheduler(goal_callback=agent.set_goal)
    scheduler.start()

    # ── System Monitor ────────────────────────────────────────────────────────
    system_monitor = None
    if not args.no_monitor:
        from core.system_monitor import SystemMonitor
        system_monitor = SystemMonitor(bus, goal_callback=agent.set_goal)
        system_monitor.start()

    # ── Proactive Monitor ─────────────────────────────────────────────────────
    if not args.no_proactive and vision_llm:
        from core.proactive_monitor import ProactiveMonitor
        ProactiveMonitor(vision_llm, bus, goal_callback=agent.set_goal).start()

    # ── Multi-Agent Manager ───────────────────────────────────────────────────
    from core.multi_agent import MultiAgentManager
    wiring.attach_multi_agent(MultiAgentManager(llm, vision_llm, config, bus))

    # ── Workflow Recorder + Converter ─────────────────────────────────────────
    from core.workflow_recorder import WorkflowRecorder
    from core.workflow_converter import WorkflowConverter
    recorder = WorkflowRecorder()
    wiring.attach_recorder(recorder)
    wiring.attach_converter(WorkflowConverter(llm, recorder))

    # ── Screen Recorder ───────────────────────────────────────────────────────
    if not args.no_recording:
        from perception.screen_recorder import ScreenRecorder
        wiring.attach_screen_recorder(ScreenRecorder())
        print("  Screen recorder: ready")

    # ── Task Templates ────────────────────────────────────────────────────────
    from core.task_templates import TaskTemplateLibrary
    templates = TaskTemplateLibrary()
    wiring.attach_templates(templates)
    print(f"  Templates: {len(templates.list_all())} loaded")

    # ── Multi-Language Support ────────────────────────────────────────────────
    def _llm_generate(messages):
        return llm.generate(messages)

    from core.multi_language import MultiLanguageSupport
    lang_support = MultiLanguageSupport(llm_generate_fn=_llm_generate)
    wiring.attach_lang_support(lang_support)
    if args.lang:
        print(f"  Language: {args.lang}")

    # ── Autonomous Learning Loop ──────────────────────────────────────────────
    learning_loop = None
    if not args.no_learning:
        from core.learning_loop import AutonomousLearningLoop
        learning_loop = AutonomousLearningLoop(
            llm_generate_fn=_llm_generate,
            semantic_memory=agent.semantic,
            episodic_memory=agent.episodic,
        )
        learning_loop.start()
        wiring.attach_learning_loop(learning_loop)
        print("  Autonomous learning loop: active (starts after 5min idle)")

    # ── Mobile Bridge (declare early so stress_detector callback can reference it)
    mobile_bridge = None

    # ── Stress Detector ───────────────────────────────────────────────────────
    stress_detector = None
    if not args.no_stress:
        from perception.stress_detector import StressDetector
        def on_stress_change(state):
            if state.level >= 3:
                bus.publish("stress_level_high", {"level": state.level, "label": state.label})
                if mobile_bridge:
                    mobile_bridge.push_notification(
                        "Stress Detected",
                        f"Stress level: {state.label}. {state.recommendations[0] if state.recommendations else ''}",
                        priority="high" if state.level >= 4 else "normal",
                    )
        stress_detector = StressDetector(on_stress_change=on_stress_change)
        stress_detector.start()
        wiring.attach_stress_detector(stress_detector)
        print("  Stress detection: active")

    # ── Remote Control Server ─────────────────────────────────────────────────
    if not args.no_remote:
        from remote.server import set_agent, start_server
        set_agent(agent, scheduler=scheduler, system_monitor=system_monitor,
                  workflow_recorder=recorder)
        start_server(port=args.remote_port)
        print(f"  Remote control: http://localhost:{args.remote_port}")

    # ── Mobile Bridge ─────────────────────────────────────────────────────────
    if not args.no_mobile:
        try:
            from remote.mobile_bridge import MobileBridge
            from perception.screen_capture import ScreenCapture
            _screen_cap = ScreenCapture()

            def on_mobile_goal(goal: str):
                # Multi-language: translate if needed
                english_goal, src_lang = lang_support.process_multilingual_goal(goal)
                agent.set_goal(english_goal)
                persistence.save(english_goal, [])
                docs.log_goal(english_goal, "mobile")
                dashboard.record_task_start(f"mobile_{id(goal)}", english_goal)

            mobile_bridge = MobileBridge(
                port=args.mobile_port,
                on_goal_received=on_mobile_goal,
                get_status_fn=lambda: {
                    "current_goal": agent.goal,
                    "is_busy": agent.running,
                },
                get_screenshot_fn=lambda: _screen_cap.capture(1),
            )
            mobile_bridge.start()
            wiring.attach_mobile_bridge(mobile_bridge)

            from remote.mobile_bridge import get_connection_info
            print(f"  Mobile app: port {args.mobile_port}")
            print(get_connection_info())
        except Exception as e:
            print(f"  Mobile bridge: failed to start — {e}")

    # ── Peer Network ──────────────────────────────────────────────────────────
    peer_network = None
    if not args.no_peers:
        try:
            from core.peer_network import PeerNetwork

            def on_peer_knowledge(fact: str, category: str):
                if agent.semantic:
                    agent.semantic.store(fact, source=f"peer:{category}", tags=["peer_knowledge"])

            def on_peer_task(goal: str):
                agent.set_goal(goal)

            peer_network = PeerNetwork(
                port=args.peer_port,
                on_task_received=on_peer_task,
                on_knowledge_received=on_peer_knowledge,
            )
            peer_network.start()
            wiring.attach_peer_network(peer_network)
            print(f"  Peer network: port {args.peer_port}")
        except Exception as e:
            print(f"  Peer network: failed — {e}")

    # ── Wake Word Detection ───────────────────────────────────────────────────
    if not args.no_wake_word:
        try:
            from audio.wake_word import WakeWordDetector
            def on_wake_word():
                print("\n🎤 Wake word detected! Listening for goal...")
                if mobile_bridge:
                    mobile_bridge.push_notification("Wake Word", "AI Human is listening...")
                # Trigger STT to get goal
                try:
                    from audio.stt import SpeechToText
                    stt = SpeechToText()
                    goal_text = stt.listen_once()
                    if goal_text:
                        print(f"  Heard: {goal_text}")
                        english_goal, _ = lang_support.process_multilingual_goal(goal_text)
                        agent.set_goal(english_goal)
                    else:
                        print("  Wake word: no speech detected (timeout)")
                except Exception as e:
                    print(f"  Wake word STT error: {e}")
            wake = WakeWordDetector(wake_word=args.wake_word)
            wake.start(callback=on_wake_word)
            print(f"  Wake word: listening for '{args.wake_word}'")
        except Exception as e:
            print(f"  Wake word: unavailable — {e}")

    # ── Browser Extension Bridge ──────────────────────────────────────────────
    try:
        from tools.built_in.browser_extension_bridge import BrowserBridge, create_extension_files
        browser_bridge = BrowserBridge()
        browser_bridge.start()
        wiring.attach_browser_bridge(browser_bridge)
        # Create extension files if not present
        if not __import__("pathlib").Path("browser_extension/manifest.json").exists():
            create_extension_files()
            print("  Browser extension: files created at browser_extension/")
        print("  Browser extension bridge: ws://localhost:8765")
    except Exception as e:
        print(f"  Browser extension bridge: unavailable — {e}")

    # ── Load Skill Packs ──────────────────────────────────────────────────────
    _load_skill_packs()
    docs.generate_tool_guide(agent.tools.all_tools())

    # ── Plugin Marketplace ────────────────────────────────────────────────────
    from plugins.marketplace import PluginMarketplace
    installed = PluginMarketplace().list_installed()
    if installed:
        print(f"  Plugins: {len(installed)} loaded")

    # ── Initial Goal ──────────────────────────────────────────────────────────
    if args.goal:
        english_goal, _ = lang_support.process_multilingual_goal(args.goal)
        agent.set_goal(english_goal)

    # ── Start Agent ───────────────────────────────────────────────────────────
    agent.start()
    print("  Agent running.\n")

    # Log startup
    docs.log_action("startup", {}, f"AI Human started with provider={config.llm_provider}")

    if args.no_ui:
        _run_headless(agent, persistence, scheduler, docs, dashboard, lang_support)
    else:
        _run_with_ui(agent, bus, config, persistence, scheduler, docs, dashboard, lang_support)


def _load_skill_packs() -> None:
    """Skill packs are now auto-loaded by ToolRegistry from skills/ directory."""
    pass


def _run_goal_with_feedback(agent, goal: str) -> None:
    """Set a goal and block, printing state changes until the agent finishes."""
    import time
    from core.agent import AgentState

    agent.set_goal(goal)
    print(f"  >> Goal set. Working...", flush=True)

    last_state = None

    # Subscribe a lightweight listener to the bus to capture action results
    import threading
    action_log = []

    def _bus_listener():
        while agent.goal:  # stop when goal is cleared
            event = agent._bus.consume(timeout=0.1)
            if event is None:
                continue
            if event.type == "action":
                d = event.data
                status = "OK" if d.get("success") else "FAILED"
                action_log.append(f"  [Action] {d.get('name')} -> {status}: {d.get('msg','')[:80]}")
            elif event.type == "error":
                action_log.append(f"  [Error]  {str(event.data)[:100]}")

    listener = threading.Thread(target=_bus_listener, daemon=True, name="HeadlessListener")
    listener.start()

    try:
        while agent.goal:
            state = agent.state.name
            if state != last_state:
                print(f"  [{state}]", flush=True)
                last_state = state
            # Flush any action logs collected by the listener
            while action_log:
                print(action_log.pop(0), flush=True)
            time.sleep(0.4)
    except KeyboardInterrupt:
        agent.set_goal("")
        print("  Interrupted.")
        return

    # Flush remaining action logs
    while action_log:
        print(action_log.pop(0), flush=True)
    print("  >> Done.\n", flush=True)


def _run_headless(agent, persistence, scheduler, docs, dashboard, lang_support) -> None:
    import time
    print("  Headless mode. Commands: <goal> | schedules | status | templates | quit\n")
    try:
        while True:
            try:
                cmd = input("Goal > ").strip()
            except EOFError:
                time.sleep(1)
                continue

            if not cmd:
                continue

            cmd_lower = cmd.lower()

            if cmd_lower in ("quit", "exit", "q"):
                break
            elif cmd_lower in ("schedules", "list schedules"):
                for t in scheduler.list_tasks():
                    print(f"  [{t['id']}] {t['schedule_type']} {t['schedule_value']} — {t['goal'][:50]}")
            elif cmd_lower == "status":
                print(docs.get_recent_log(n=20))
            elif cmd_lower == "report":
                path = dashboard.save_report()
                print(f"  Report saved: {path}")
            elif cmd_lower == "templates":
                from core.task_templates import TaskTemplateLibrary
                print(TaskTemplateLibrary().to_summary_list())
            elif cmd_lower.startswith("template "):
                template_id = cmd[9:].strip()
                from core.task_templates import TaskTemplateLibrary
                goal = TaskTemplateLibrary().instantiate(template_id)
                if goal:
                    agent.set_goal(goal)
                    persistence.save(goal, agent.context_window)
                else:
                    print(f"  Template '{template_id}' not found")
            elif cmd_lower.startswith("schedule "):
                # "schedule every day at 9am: check emails"
                parts = cmd[9:].split(":", 1)
                if len(parts) == 2:
                    from core.nl_scheduler import NLScheduler
                    nl = NLScheduler()
                    sched = nl.parse(parts[0].strip())
                    goal_str = parts[1].strip()
                    # Translate ParsedSchedule → Scheduler.add(type, value, goal)
                    if sched.type == "once" and sched.run_at:
                        scheduler.add("once", sched.run_at.strftime("%Y-%m-%d %H:%M"), goal_str)
                    elif sched.type == "daily" and sched.hour is not None:
                        scheduler.add("every_day", f"{sched.hour:02d}:{sched.minute or 0:02d}", goal_str)
                    elif sched.type == "interval" and sched.interval_seconds:
                        scheduler.add("interval", sched.interval_seconds, goal_str)
                    elif sched.type in ("weekly", "monthly", "cron"):
                        scheduler.add("cron", sched.to_cron_expression(), goal_str)
                    else:
                        scheduler.add("every_day", "09:00", goal_str)
                    print(f"  Scheduled: {nl.describe(sched)}")
                else:
                    print("  Format: schedule <when>: <goal>")
            else:
                # Translate if needed
                english_goal, src_lang = lang_support.process_multilingual_goal(cmd)
                if src_lang != "en":
                    print(f"  (Translated from {src_lang}): {english_goal}")
                persistence.save(english_goal, agent.context_window)
                docs.log_goal(english_goal)
                _run_goal_with_feedback(agent, english_goal)

    except KeyboardInterrupt:
        pass
    finally:
        docs.flush()
        agent.stop()
        persistence.clear()
        print("\nAI Human stopped.")


def _run_with_ui(agent, bus, config, persistence, scheduler, docs, dashboard, lang_support) -> None:
    if not config.show_avatar:
        _run_headless(agent, persistence, scheduler, docs, dashboard, lang_support)
        return
    try:
        from avatar.app import AvatarApp

        def on_goal(goal: str):
            english_goal, src_lang = lang_support.process_multilingual_goal(goal)
            agent.set_goal(english_goal)
            persistence.save(english_goal, agent.context_window)
            docs.log_goal(english_goal)

        AvatarApp(bus, on_goal_submit=on_goal).run()
    except Exception as e:
        print(f"  Avatar UI failed ({e}). Falling back to headless.")
        _run_headless(agent, persistence, scheduler, docs, dashboard, lang_support)
    finally:
        docs.flush()
        agent.stop()
        persistence.clear()


if __name__ == "__main__":
    main()
