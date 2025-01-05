import datetime
import operator
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from loguru import logger
from config import AgentConfig, TOOLS

# 📌 Chargement des variables d'environnement
_ = load_dotenv()

# 🗓️ Obtention de l'année courante pour le contexte
CURRENT_YEAR = datetime.datetime.now().year
MONTH = datetime.datetime.now().month


# 🏗️ Définition de la structure d'état de l'agent
class AgentState(TypedDict):
    # Liste des messages avec annotation pour l'opérateur d'addition
    messages: Annotated[list[AnyMessage], operator.add]


# 🤖 Prompt système pour la recherche de vols et hôtels
TOOLS_SYSTEM_PROMPT = """You are specialized in job search analysis. Your role is to use the provided job search tools effectively to find relevant job opportunities based on user requirements.

Follow these guidelines:
- Analyze the user's job search requirements carefully
- Use the jobs_finder tool with appropriate parameters
- Filter and prioritize the most relevant opportunities
- Present results in a clear, organized manner

Example interaction:
User: "Find senior developer roles in Paris with Python skills"
Assistant thought process:
1. Keywords: ["Senior Developer", "Python Developer"]
2. Location: "Paris"
3. Required skills: ["Python"]
4. Experience level: ["Senior"]
5. Time frame: Recent postings - "WEEK"

Tool call:
{
    "params": {
        "keywords": ["Senior Developer", "Python Developer"],
        "location": "Paris",
        "required_skills": ["Python"],
        "experience_level": ["Senior"],
        "posted_time": "WEEK",
        "remote_options": ["REMOTE", "HYBRID", "ON-SITE"]
    }
}

When analyzing results:
1. Verify job relevancy
2. Check if skills match requirements 
3. Validate location and working conditions
4. Ensure salary range matches seniority (if provided)
5. Confirm posting recency

Always prioritize:
- Skill match accuracy
- Location relevance
- Posting freshness
- Company reputation (if available)
"""


class Agent:
    def __init__(self, config: AgentConfig = None):
        self.config = config if config is not None else AgentConfig()
        self._tools = {t.name: t for t in TOOLS}
        self._tools_llm = ChatOpenAI(
            model=self.config.model, temperature=self.config.temperature
        ).bind_tools(TOOLS)
        self._system_prompt = self._build_system_prompt()

        # Construction du graphe
        builder = StateGraph(AgentState)
        builder.add_node("call_tools_llm", self.call_tools_llm)
        builder.add_node("invoke_tools", self.invoke_tools)
        builder.set_entry_point("call_tools_llm")

        builder.add_conditional_edges(
            "call_tools_llm",
            Agent.exists_action,
            {"more_tools": "invoke_tools"},
        )
        builder.add_edge("invoke_tools", "call_tools_llm")
        self.graph = builder

        logger.info(self.graph.get_graph().draw_mermaid())

    def _build_system_prompt(self) -> str:
        """Construit le prompt système"""
        base_prompt = TOOLS_SYSTEM_PROMPT

        if self.config.preferences:
            preferences_str = ", ".join(self.config.preferences)
            base_prompt += f"\nJob preferences: {preferences_str}"

        base_prompt += (
            f"\nSearch limits: up to {self.config.max_results} jobs per search"
        )

        return base_prompt

    @staticmethod
    def exists_action(state: AgentState):
        """Détermine l'action suivante"""
        result = state["messages"][-1]
        if len(result.tool_calls) == 0:
            return "end"
        return "more_tools"

    def call_tools_llm(self, state: AgentState):
        """Appelle le LLM avec le contexte"""
        messages = state["messages"]
        messages = [SystemMessage(content=self._system_prompt)] + messages
        message = self._tools_llm.invoke(messages)
        return {"messages": [message]}

    def invoke_tools(self, state: AgentState):
        """Exécute les outils demandés"""
        tool_calls = state["messages"][-1].tool_calls
        results = []

        for t in tool_calls:
            logger.info(f"✨ Starting tool execution: {t['name']}")
            logger.info(f"📝 Arguments: {t['args']}")

            try:
                if t["name"] not in self._tools:
                    logger.error(f"❌ Unknown tool: {t['name']}")
                    result = "Tool not found"
                else:
                    # Préparation des arguments pour jobs_finder
                    if t["name"] == "jobs_finder":
                        if "params" not in t["args"]:
                            t["args"]["params"] = {}

                        logger.info(
                            f"🔍 Job search params before update: {t['args']['params']}"
                        )

                        t["args"]["params"].update(
                            {
                                "required_skills": self.config.required_skills,
                                "remote_options": self.config.remote_options,
                                "contract_type": "Prestataire",  # Par défaut en mode prestataire
                            }
                        )

                        logger.info(
                            f"✨ Job search params after update: {t['args']['params']}"
                        )

                    result = self._tools[t["name"]].invoke(t["args"])
                    logger.info(f"✅ Tool execution completed: {t['name']}")

            except Exception as e:
                logger.error(f"❌ Error executing {t['name']}: {str(e)}")
                result = f"Error: {str(e)}"

            results.append(
                ToolMessage(tool_call_id=t["id"], name=t["name"], content=str(result))
            )

        return {"messages": results}
