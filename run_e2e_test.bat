@echo off
:: ============================================================
::  AI Human - End-to-End System Test
::  Tests: config -> LLM -> screenshot -> vision -> OCR ->
::         tools -> safety -> action -> full agent init
:: ============================================================

set LLM_PROVIDER=anthropic
set LLM_MODEL=claude-haiku-4-5-20251001
set AI_HUMAN_HEADLESS_CONFIRM=allow

:: Set your Anthropic key here if not already in .env
:: set ANTHROPIC_API_KEY=sk-ant-xxxxx

cd /d %~dp0
echo.
echo ============================================================
echo   AI Human - End-to-End Test
echo ============================================================
echo.

python -c "
import sys, os, time
sys.path.insert(0, '.')

PASS = '[PASS]'
FAIL = '[FAIL]'
WARN = '[WARN]'
results = []

def check(label, fn):
    try:
        result = fn()
        print(f'  {PASS} {label}' + (f': {result}' if result else ''))
        results.append((label, True, None))
        return result
    except Exception as e:
        print(f'  {FAIL} {label}: {e}')
        results.append((label, False, str(e)))
        return None

print('--- 1. CONFIG ---')
config = None
def load_config():
    global config
    from config import get_config
    config = get_config()
    return f'provider={config.llm_provider} | model={config.llm_model or \"(auto)\"}'
check('Config load', load_config)

print()
print('--- 2. LLM ---')
llm = None
vision_llm = None
def load_llm():
    global llm
    from llm.factory import create_llm
    llm = create_llm(config, model_type='text')
    return llm.model_name
check('LLM init', load_llm)

def test_llm_call():
    from llm.message_builder import system_message, text_message
    msgs = [system_message('You are a test assistant.'), text_message('user', 'Reply with exactly one word: OK')]
    resp = llm.generate(msgs)
    assert resp and len(resp) > 0, 'Empty LLM response'
    return repr(resp.strip()[:60])
check('LLM generate() real API call', test_llm_call)

def load_vision():
    global vision_llm
    if llm and llm.supports_vision():
        vision_llm = llm
        return 'same as LLM (supports vision)'
    elif config and config.vision_model:
        from llm.factory import create_llm
        vision_llm = create_llm(config, model_type='vision')
        return vision_llm.model_name
    return 'no vision model — OCR-only mode'
check('Vision LLM', load_vision)

print()
print('--- 3. SCREEN CAPTURE ---')
screenshot = None
def capture():
    global screenshot
    from perception.screen_capture import ScreenCapture
    screenshot = ScreenCapture().capture()
    assert screenshot is not None
    return f'{screenshot.size[0]}x{screenshot.size[1]} px'
check('Screenshot capture', capture)

print()
print('--- 4. VISION / OCR ---')
def test_ocr():
    from perception.ocr_engine import OCREngine
    ocr = OCREngine()
    text = ocr.extract_text(screenshot)
    words = len(text.split())
    if words == 0:
        print(f'  {WARN} OCR: 0 words — Tesseract may not be installed')
        print(f'        Install: https://github.com/UB-Mannheim/tesseract/wiki')
        return 'Tesseract not found (install for OCR support)'
    return f'{words} words extracted'
check('OCR text extraction', test_ocr)

def test_vision_analysis():
    from perception.vision_analyzer import VisionAnalyzer
    from perception.ocr_engine import OCREngine
    analyzer = VisionAnalyzer(vision_llm=vision_llm, ocr=OCREngine())
    desc = analyzer.analyze(screenshot)
    assert desc and len(desc) > 5, 'Empty vision description'
    return desc[:80]
check('Vision screen analysis (LLM sees screenshot)', test_vision_analysis)

print()
print('--- 5. TOOL REGISTRY ---')
registry = None
def load_tools():
    global registry
    from tools.registry import ToolRegistry
    registry = ToolRegistry()
    count = registry.tool_count()
    assert count > 0, 'No tools loaded'
    names = [t.name for t in registry.all_tools()[:4]]
    return f'{count} tools | sample: {names}'
check('Tool registry auto-discovery', load_tools)

print()
print('--- 6. MEMORY ---')
def test_memory():
    from memory.semantic import SemanticMemory
    mem = SemanticMemory(config)
    mem.store('e2e test ping', source='test', tags=['test'])
    results_m = mem.search('test ping', n=1)
    return f'ChromaDB write+search OK ({len(results_m)} result)'
check('Semantic memory (ChromaDB)', test_memory)

print()
print('--- 7. SAFETY BROKER ---')
def test_safety():
    from safety.broker import SafetyBroker, SafetyBlock
    from safety.audit_log import AuditLog
    broker = SafetyBroker(config, AuditLog())
    broker.check('screenshot', {})
    try:
        broker.check('format_disk', {'drive': 'C:'})
        raise AssertionError('Destructive action was NOT blocked!')
    except SafetyBlock:
        return 'low-risk allowed | destructive correctly blocked'
check('Safety broker', test_safety)

print()
print('--- 8. ACTION EXECUTOR ---')
def test_action():
    from actions.executor import ActionExecutor
    executor = ActionExecutor()
    result = executor.execute('move', {'x': 200, 'y': 200})
    assert result.success, f'move failed: {result.message}'
    return result.message
check('Action: move mouse to (200,200)', test_action)

def test_click_action():
    from actions.executor import ActionExecutor
    executor = ActionExecutor()
    result = executor.execute('screenshot', {})
    assert result.success, f'screenshot action failed: {result.message}'
    return result.message[:60]
check('Action: screenshot', test_click_action)

print()
print('--- 9. AGENT ORCHESTRATOR ---')
def test_agent_init():
    from core.agent import AgentOrchestrator
    from core.event_bus import EventBus
    bus = EventBus()
    agent = AgentOrchestrator(config, llm, vision_llm, bus)
    assert agent is not None
    assert agent.tools.tool_count() > 0
    return f'state={agent.state.name} | tools={agent.tools.tool_count()}'
check('AgentOrchestrator init + wiring', test_agent_init)

print()
print('--- 10. FULL AGENT TICK ---')
def test_one_tick():
    from core.agent import AgentOrchestrator
    from core.event_bus import EventBus
    bus = EventBus()
    agent = AgentOrchestrator(config, llm, vision_llm, bus)
    agent.set_goal('Take a screenshot and describe what you see on screen in one sentence')
    agent.start()
    time.sleep(10)
    agent.stop()
    return f'completed one tick | final state={agent.state.name}'
check('Full perceive-think-act-learn tick (10s)', test_one_tick)

print()
print('============================================================')
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)
print(f'  Results: {passed}/{total} passed', end='')
if failed:
    print(f'   |   {failed} FAILED:')
    for label, ok, err in results:
        if not ok:
            print(f'      - {label}')
            print(f'        {err}')
    print()
    print('  Fix the failures above then run again.')
else:
    print()
    print()
    print('  ALL SYSTEMS GO')
    print('  Run the agent: python main.py --no-wake-word')
print('============================================================')
"

echo.
pause
