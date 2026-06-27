# ruff: noqa
import re
import sys
import json
import os
import logging
import datetime
from google.adk import Agent, Workflow, Event, Context
from google.adk.models import Gemini
from google.adk.events import RequestInput
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types
from app.config import config

logger = logging.getLogger(__name__)

# Helper to log security events
def log_security_event(event_type: str, severity: str, details: dict):
    audit_log = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "severity": severity,
        "details": details
    }
    print(json.dumps(audit_log))

# PII Scrubbing patterns
def scrub_pii(text: str) -> str:
    # Email regex
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_REDACTED]", text)
    # Phone number regex
    text = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]", text)
    # US SSN regex
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", text)
    return text

# Prompt injection detection keywords
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "system prompt",
    "jailbreak",
    "override",
    "bypass rules",
    "you are no longer",
    "dan mode",
    "do anything now"
]

def detect_injection(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in INJECTION_KEYWORDS)

# Academic integrity cheating pattern
def check_academic_integrity(text: str) -> bool:
    text_lower = text.lower()
    cheating_patterns = [
        r"\b(?:test|exam|quiz)\s+question\b",
        r"\b(?:what is the)?\s*answer to\s+(?:q|question)\b"
    ]
    return any(re.search(pat, text_lower) for pat in cheating_patterns)

# Setup MCP server connection parameters dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
mcp_server_path = os.path.join(current_dir, "mcp_server.py")

mcp_connection = StdioConnectionParams(
    server_params=StdioServerParameters(
        command=sys.executable,
        args=[mcp_server_path]
    )
)

# 1. Specialized Sub-Agents with MCP Tools Wired
study_planner = Agent(
    name="study_planner",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Study Planner Agent. 
Your job is to take a subject, syllabus details, or exam topic, and create a structured study schedule.
Include weekly/daily breakdown of tasks, time allocation, and recommended learning techniques.
You have access to the `get_study_tips` tool from the MCP server. Use it to suggest specific, tailored study tips based on the student's learning style!
Make the schedule practical, encouraging, and easy to follow, especially for students who might have limited resources.""",
    tools=[
        McpToolset(
            connection_params=mcp_connection,
            tool_filter=["get_study_tips"]
        )
    ],
    description="Tool to generate structured study plans and schedules.",
)

quiz_generator = Agent(
    name="quiz_generator",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Quiz Generator Agent.
Your job is to generate study aids such as mock quizzes, practice questions, and flashcard content for any academic topic.
You have access to the `create_mnemonic` tool from the MCP server. If there is a list of terms or steps that the student needs to memorize, use this tool to generate a fun, memorable mnemonic for them!
Always include an answer key at the bottom with brief explanations of why each answer is correct.
Tailor the difficulty to the level requested by the student.""",
    tools=[
        McpToolset(
            connection_params=mcp_connection,
            tool_filter=["create_mnemonic"]
        )
    ],
    description="Tool to generate mock quizzes and practice questions with explanations.",
)

explanation_helper = Agent(
    name="explanation_helper",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Explanation Agent.
Your job is to explain complex academic concepts in simple, accessible language.
Use relatable analogies, real-world examples, and step-by-step breakdowns.
You have access to the `simplify_formula` tool from the MCP server. If the concept involves a math or science formula, use this tool to help break it down!
Avoid overly academic jargon, or explain the jargon if it must be used. Keep it engaging.""",
    tools=[
        McpToolset(
            connection_params=mcp_connection,
            tool_filter=["simplify_formula"]
        )
    ],
    description="Tool to explain difficult academic topics using simple analogies.",
)

notes_generator = Agent(
    name="notes_generator",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Notes Generator Agent.
Your job is to create chapter summaries, key points, important definitions, mind maps (text-based), and formula sheets.
Make the notes concise, highly structured, and easy to read/revise.""",
    description="Tool to generate structured revision notes, summaries, and formula sheets.",
)

progress_tracker = Agent(
    name="progress_tracker",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Progress Tracker Agent.
Your job is to review the student's current progress state and help them update it or summarize what they have achieved.
If they completed a topic, explicitly state in your output: "mark [Topic Name] as completed".
If they share a quiz score, explicitly state: "score: [Score]% on [Topic Name]".
Review their weak topics, strong topics, and suggest what they should study next based on their progress.""",
    description="Tool to check, log, and summarize student learning progress.",
)

revision_planner = Agent(
    name="revision_planner",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Revision Planner Agent.
Your job is to design short-term revision plans when exams are close.
Take the remaining days, the subject, and any weak topics from the student's progress and build a highly optimized revision calendar.
Include Mock Tests, Quick Revisions, and flashcard sessions to maximize preparation in minimum time.""",
    description="Tool to generate optimized short-term revision plans and schedules.",
)

resource_finder = Agent(
    name="resource_finder",
    model=Gemini(model=config.model),
    instruction="""You are a specialized Resource Finder Agent.
Your job is to recommend top-quality, free educational resources for any given topic.
Suggest YouTube channels/videos (e.g., Khan Academy, CrashCourse, Amoeba Sisters, NPTEL), free textbook PDFs, open courseware, and practice papers.
Make your recommendations highly relevant, specific, and accessible for students from underprivileged backgrounds.""",
    description="Tool to find free, high-quality educational resources, videos, and books.",
)

# 2. Main Orchestrator Agent (Intent Router)
intent_router = Agent(
    name="intent_router",
    model=Gemini(model=config.model),
    instruction="""You are the EduForge Intent Router and Coordinator Agent. 
Your goal is to assist students from underprivileged backgrounds in their education by routing their requests to specialized agents and keeping track of their learning state.

Analyze the user's request:
1. If the user wants a study plan or schedule, call the study_planner tool.
2. If the user wants a quiz or practice questions, call the quiz_generator tool.
3. If the user wants an explanation of a concept, call the explanation_helper tool.
4. If the user wants notes, summaries, mind maps, or formula sheets, call the notes_generator tool.
5. If the user wants to check progress, log a completed chapter, log a score, or ask what to do next, call the progress_tracker tool.
6. If the user has an exam coming up soon and needs an optimized revision schedule, call the revision_planner tool.
7. If the user is struggling and needs external learning resources (videos, PDFs, papers), call the resource_finder tool.

If the user's request is ambiguous or spans multiple categories, you can call multiple tools or ask the student for clarification.
Once you receive the response from the sub-agent(s), present the result to the student in a clear, supportive, and encouraging tone.
Always let the student know they can ask for changes or revisions in the next step.""",
    tools=[
        AgentTool(agent=study_planner),
        AgentTool(agent=quiz_generator),
        AgentTool(agent=explanation_helper),
        AgentTool(agent=notes_generator),
        AgentTool(agent=progress_tracker),
        AgentTool(agent=revision_planner),
        AgentTool(agent=resource_finder),
    ],
    description="Coordinator Agent that routes user intents to specialized sub-agents.",
)

# 3. Workflow Function Nodes
def security_checkpoint(node_input: str, ctx: Context) -> Event:
    # Initialize / increment session revision count
    if "revision_count" not in ctx.state:
        ctx.state["revision_count"] = 0
    else:
        ctx.state["revision_count"] += 1

    log_details = {
        "input_length": len(node_input) if node_input else 0,
        "revision_count": ctx.state["revision_count"]
    }

    if not node_input or not isinstance(node_input, str):
        log_security_event("empty_input", "WARNING", log_details)
        return Event(route="PASS", message="", output="")

    # Check if revision limit is exceeded
    if ctx.state["revision_count"] > 3:
        log_details["reason"] = "Revision rate limit exceeded"
        log_security_event("rate_limit_exceeded", "WARNING", log_details)
        ctx.state["security_error"] = "You have reached the maximum number of revisions for this session. Let's wrap up!"
        return Event(route="FINISH", message="Revision limit reached.", output="Revision limit reached.")

    # Check if user is requesting to finish the session
    input_clean = node_input.strip().lower()
    if input_clean in ["done", "exit", "quit", "no", "n", "thanks", "thank you"]:
        log_security_event("session_finished", "INFO", log_details)
        return Event(route="FINISH", message=node_input, output=node_input)

    # Prompt injection check
    if detect_injection(node_input):
        log_details["reason"] = "Prompt injection keywords detected"
        log_security_event("security_violation", "CRITICAL", log_details)
        ctx.state["security_error"] = "Input contains potential prompt injection attempt."
        return Event(route="SECURITY_EVENT", message="Security violation detected.", output="Security violation detected.")

    # Academic integrity check
    if check_academic_integrity(node_input):
        log_details["reason"] = "Academic integrity violation detected"
        log_security_event("security_violation", "WARNING", log_details)
        ctx.state["security_error"] = "EduForge is designed to help you learn, not to do your exams or homework directly. Please ask for an explanation, study guide, or quiz instead!"
        return Event(route="SECURITY_EVENT", message="Security violation detected.", output="Security violation detected.")

    # PII scrubbing
    scrubbed = scrub_pii(node_input)
    if scrubbed != node_input:
        log_details["pii_redacted"] = True
        log_security_event("pii_scrubbed", "INFO", log_details)
    else:
        log_security_event("input_passed", "INFO", log_details)

    # Append progress context to prompt if it exists in state
    progress = ctx.state.get("progress", {})
    if progress:
        progress_str = json.dumps(progress)
        scrubbed = f"{scrubbed}\n\n[System Memory - Current Progress: {progress_str}]"

    return Event(route="PASS", message=scrubbed, output=scrubbed)

def security_failure(node_input: str, ctx: Context) -> Event:
    error_msg = ctx.state.get("security_error", "Access Denied due to Security Policy.")
    return Event(
        message=f"🛑 Security Check Failed:\n\n{error_msg}\n\nPlease try again with a valid educational query.",
        output="Security failure"
    )

def update_progress_state(node_input: str, ctx: Context) -> Event:
    # Initialize progress structure in state if missing
    if "progress" not in ctx.state:
        ctx.state["progress"] = {
            "completed_chapters": [],
            "quiz_scores": {},
            "weak_topics": [],
            "strong_topics": []
        }
    
    # Check if sub-agent output instructs a progress update
    match_completed = re.search(r"mark\s+\[?([\w\s\-]+)\]?\s+as\s+completed", node_input, re.IGNORECASE)
    if match_completed:
        chapter = match_completed.group(1).strip()
        if chapter not in ctx.state["progress"]["completed_chapters"]:
            ctx.state["progress"]["completed_chapters"].append(chapter)
            
    match_score = re.search(r"score:\s*(\d+)%\s+on\s+\[?([\w\s\-]+)\]?", node_input, re.IGNORECASE)
    if match_score:
        score = int(match_score.group(1))
        topic = match_score.group(2).strip()
        ctx.state["progress"]["quiz_scores"][topic] = score
        if score >= 80:
            if topic not in ctx.state["progress"]["strong_topics"]:
                ctx.state["progress"]["strong_topics"].append(topic)
            if topic in ctx.state["progress"]["weak_topics"]:
                ctx.state["progress"]["weak_topics"].remove(topic)
        else:
            if topic not in ctx.state["progress"]["weak_topics"]:
                ctx.state["progress"]["weak_topics"].append(topic)
            if topic in ctx.state["progress"]["strong_topics"]:
                ctx.state["progress"]["strong_topics"].remove(topic)

    return Event(route="PASS", message=node_input, output=node_input)

async def feedback_requester(node_input: str, ctx: Context):
    # Ask the student if they want revisions
    yield RequestInput(
        message=f"{node_input}\n\n---\nWould you like to make any revisions, log more progress, or change anything? (Type details, or type 'done' to finish):",
        response_schema=str
    )

def final_output(node_input: str, ctx: Context) -> Event:
    limit_msg = ctx.state.get("security_error", "")
    if "limit reached" in limit_msg.lower():
        return Event(
            message=f"🛑 {limit_msg}\n\nThank you for using EduForge Assistant! Keep studying hard!",
            output="Finished"
        )
    return Event(
        message="✨ Thank you for using EduForge Assistant! Keep studying hard and unlocking your potential! Goodbye!",
        output="Finished"
    )

# 4. Assemble the Graph-based Workflow
root_agent = Workflow(
    name="eduforge_workflow",
    edges=[
        ("START", security_checkpoint),
        (security_checkpoint, {
            "PASS": intent_router,
            "SECURITY_EVENT": security_failure,
            "FINISH": final_output
        }),
        (intent_router, update_progress_state),
        (update_progress_state, feedback_requester),
        (feedback_requester, security_checkpoint)
    ]
)

app = root_agent

