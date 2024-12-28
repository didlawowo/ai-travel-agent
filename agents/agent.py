import datetime
import operator
import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
TOOLS_SYSTEM_PROMPT = f"""You are a smart travel agency. Use the tools to look up information.
    You are allowed to make multiple calls (either together or in sequence).
    Only look up information when you are sure of what you want.
    The current date is year {CURRENT_YEAR} month {MONTH} , but be carefull if someone wants informations for january and we are on december maybe its for the next year
    If you need to look up some information before asking a follow up question, you are allowed to do that!
    I want to have in your output links to hotels websites and flights websites (if possible).
    I want to have as well the logo of the hotel and the logo of the airline company (if possible).
    In your output always include the price of the flight and the price of the hotel and the currency as well (if possible).
    for example for hotels-
    Rate: $581 per night
    Total: $3,488
    """

# 🛠️ Liste des outils disponibles


# 📧 Prompt système pour la génération d'emails
EMAILS_SYSTEM_PROMPT = """Your task is to convert structured markdown-like text into a valid HTML email body.

- Do not include a ```html preamble in your response.
- The output should be in proper HTML format, ready to be used as the body of an email.
Here is an example:
<example>
Input:

I want to travel to New York from Madrid from October 1-7. Find me flights and 4-star hotels.

Expected Output:

<!DOCTYPE html>
<html>
<head>
    <title>Flight and Hotel Options</title>
</head>
<body>
    <h2>Flights from Madrid to New York</h2>
    <ol>
        <li>
            <strong>American Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:25 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:25 PM<br>
            <strong>Duration:</strong> 8 hours<br>
            <strong>Aircraft:</strong> Boeing 777<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/AA.png" alt="American Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Iberia</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 12:25 PM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 2:40 PM<br>
            <strong>Duration:</strong> 8 hours 15 minutes<br>
            <strong>Aircraft:</strong> Airbus A330<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/IB.png" alt="Iberia"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Delta Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:00 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:30 PM<br>
            <strong>Duration:</strong> 8 hours 30 minutes<br>
            <strong>Aircraft:</strong> Boeing 767<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $738<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/DL.png" alt="Delta Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
    </ol>

    <h2>4-Star Hotels in New York</h2>
    <ol>
        <li>
            <strong>NobleDen Hotel</strong><br>
            <strong>Description:</strong> Modern, polished hotel offering sleek rooms, some with city-view balconies, plus free Wi-Fi.<br>
            <strong>Location:</strong> Near Washington Square Park, Grand St, and JFK Airport.<br>
            <strong>Rate per Night:</strong> $537<br>
            <strong>Total Rate:</strong> $3,223<br>
            <strong>Rating:</strong> 4.8/5 (656 reviews)<br>
            <strong>Amenities:</strong> Free Wi-Fi, Parking, Air conditioning, Restaurant, Accessible, Business centre, Child-friendly, Smoke-free property<br>
            <img src="https://lh5.googleusercontent.com/p/AF1QipNDUrPJwBhc9ysDhc8LA822H1ZzapAVa-WDJ2d6=s287-w287-h192-n-k-no-v1" alt="NobleDen Hotel"><br>
            <a href="http://www.nobleden.com/">Visit Website</a>
        </li>
        <!-- More hotel entries here -->
    </ol>
</body>
</html>

</example>


"""


class Agent:
    def __init__(self, config: AgentConfig = None):
        # 🔧 Initialisation des outils
        self.config = config if config is not None else AgentConfig()
        self._tools = {t.name: t for t in TOOLS}
        # 🧠 Configuration du modèle LLM avec les outils
        self._tools_llm = ChatOpenAI(
            model=self.config.model, temperature=self.config.temperature
        ).bind_tools(TOOLS)
        self._system_prompt = self._build_system_prompt()
        # 📊 Construction du graphe d'état
        builder = StateGraph(AgentState)

        # Ajout des noeuds du graphe
        builder.add_node("call_tools_llm", self.call_tools_llm)  # Appel au LLM
        builder.add_node("invoke_tools", self.invoke_tools)  # Exécution des outils
        builder.add_node("email_sender", self.email_sender)  # Envoi d'email

        # Configuration du point d'entrée
        builder.set_entry_point("call_tools_llm")

        # 🔄 Configuration des transitions entre les états
        builder.add_conditional_edges(
            "call_tools_llm",
            Agent.exists_action,
            {"more_tools": "invoke_tools", "email_sender": "email_sender"},
        )
        builder.add_edge("invoke_tools", "call_tools_llm")
        builder.add_edge("email_sender", END)

        # 💾 Configuration de la sauvegarde mémoire
        memory = MemorySaver()
        self.graph = builder.compile(
            checkpointer=memory, interrupt_before=["email_sender"]
        )

        # 📝 Journalisation du graphe en format Mermaid
        logger.info(self.graph.get_graph().draw_mermaid())

    def _build_system_prompt(self) -> str:
        """Construit le prompt système en incluant les préférences"""
        base_prompt = TOOLS_SYSTEM_PROMPT

        # Ajout des préférences au prompt
        if self.config.preferences:
            preferences_str = ", ".join(self.config.preferences)
            base_prompt += f"\nTravel preferences: {preferences_str}"

        # Ajout de la devise préférée
        base_prompt += f"\nPreferred currency: {self.config.currency}"

        # Ajout des limites de recherche
        base_prompt += f"\nSearch limits: up to {self.config.max_hotels} hotels and {self.config.max_flights} flights"

        return base_prompt

    @staticmethod
    def exists_action(state: AgentState):
        """
        🔍 Détermine l'action suivante en fonction des appels d'outils
        Retourne 'email_sender' si pas d'appels d'outils, sinon 'more_tools'
        """
        result = state["messages"][-1]
        if len(result.tool_calls) == 0:
            return "email_sender"
        return "more_tools"

    def email_sender(self, state: AgentState):
        """
        📨 Gère la génération et l'envoi d'emails
        Utilise GPT-4 pour générer le contenu HTML et SendGrid pour l'envoi
        """
        logger.info("Sending email")
        # Configuration du LLM pour la génération d'email
        email_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

        # Préparation du message pour la génération
        email_message = [
            SystemMessage(content=EMAILS_SYSTEM_PROMPT),
            HumanMessage(content=state["messages"][-1].content),
        ]

        # Génération du contenu de l'email
        email_response = email_llm.invoke(email_message)
        logger.info("Email content:", email_response.content)

        # Configuration et envoi de l'email via SendGrid
        message = Mail(
            from_email=os.environ["FROM_EMAIL"],
            to_emails=os.environ["TO_EMAIL"],
            subject=os.environ["EMAIL_SUBJECT"],
            html_content=email_response.content,
        )
        try:
            sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
            response = sg.send(message)
            logger.info(response.status_code)
            logger.info(response.body)
            logger.info(response.headers)
        except Exception as e:
            logger.error(str(e))

    def call_tools_llm(self, state: AgentState):
        """
        🤖 Appelle le LLM avec le contexte système et les messages
        Retourne la réponse du LLM
        """
        messages = state["messages"]
        messages = [SystemMessage(content=TOOLS_SYSTEM_PROMPT)] + messages
        message = self._tools_llm.invoke(messages)
        return {"messages": [message]}

    def invoke_tools(self, state: AgentState):
        """
        🛠️ Exécute les outils demandés par le LLM
        """
        tool_calls = state["messages"][-1].tool_calls
        results = []

        for t in tool_calls:
            logger.info(f"✨ Starting tool execution: {t['name']}")
            logger.info(f"📝 Original arguments: {t['args']}")

            try:
                if t["name"] not in self._tools:
                    logger.error(f"❌ Unknown tool: {t['name']}")
                    result = "bad tool name, retry"
                else:
                    # Préparation des arguments selon le type d'outil
                    if t["name"] == "flights_finder":
                        if "params" not in t["args"]:
                            t["args"]["params"] = {}

                        # Log avant modification
                        logger.info(
                            f"🛫 Flight finder params before update: {t['args']['params']}"
                        )

                        # Mettre à jour les paramètres de vol
                        t["args"]["params"].update(
                            {
                                "max_results": self.config.max_flights,
                                "currency": self.config.currency,
                                "preferences": self.config.preferences,
                                "sort_by": "price",
                            }
                        )

                        # Log après modification
                        logger.info(
                            f"✈️ Flight finder params after update: {t['args']['params']}"
                        )

                    elif t["name"] == "hotels_finder":
                        if "params" not in t["args"]:
                            t["args"]["params"] = {}

                        t["args"]["params"].update(
                            {
                                "max_results": self.config.max_hotels,
                                "currency": self.config.currency,
                                "preferences": self.config.preferences,
                            }
                        )

                    # Exécution de l'outil
                    logger.info(f"🚀 Executing {t['name']} with args: {t['args']}")
                    result = self._tools[t["name"]].invoke(t["args"])
                    logger.info(f"✅ Tool execution completed: {t['name']}")

            except Exception as e:
                logger.error(f"❌ Error executing {t['name']}: {str(e)}")
                result = f"Error: {str(e)}"

            results.append(
                ToolMessage(tool_call_id=t["id"], name=t["name"], content=str(result))
            )

        logger.info("➡️ Returning results to model")
        return {"messages": results}
