import os
import uuid
import streamlit as st
from langchain_core.messages import HumanMessage
from agents.agent import Agent
from config import AgentConfig, TOOLS
from langchain_openai import ChatOpenAI


# 🔧 Fonctions de configuration
def populate_envs(sender_email, receiver_email, subject):
    """Configuration des variables d'environnement pour l'envoi d'email"""
    os.environ["FROM_EMAIL"] = sender_email
    os.environ["TO_EMAIL"] = receiver_email
    os.environ["EMAIL_SUBJECT"] = subject


def send_email(sender_email, receiver_email, subject, thread_id):
    """Gestion de l'envoi d'email avec gestion des erreurs"""
    try:
        populate_envs(sender_email, receiver_email, subject)
        config = {"configurable": {"thread_id": thread_id}}
        st.session_state.agent.graph.invoke(None, config=config)
        st.success("Email sent successfully!")
        # Nettoyage de la session
        for key in ["travel_info", "thread_id"]:
            st.session_state.pop(key, None)
    except Exception as e:
        st.error(f"Error sending email: {e}")


# 🤖 Initialisation de l'agent
def initialize_agent():
    """Initialise ou met à jour l'agent avec la configuration"""
    if "agent_params" in st.session_state:
        config = AgentConfig(**st.session_state.agent_params)
        if "agent" not in st.session_state:
            st.session_state.agent = Agent(config=config)
        else:
            # Mise à jour de la configuration existante
            st.session_state.agent.config = config
            st.session_state.agent._tools_llm = ChatOpenAI(
                model=config.model, temperature=config.temperature
            ).bind_tools(TOOLS)
            st.session_state.agent._system_prompt = (
                st.session_state.agent._build_system_prompt()
            )
    else:
        if "agent" not in st.session_state:
            st.session_state.agent = Agent()


# 🎨 Style CSS personnalisé
def render_custom_css():
    """Applique le style CSS personnalisé à l'interface"""
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.5em;
            color: #333;
            text-align: center;
            margin-bottom: 0.5em;
            font-weight: bold;
        }
        .sub-title {
            font-size: 1.2em;
            color: #333;
            text-align: left;
            margin-bottom: 0.5em;
        }
        .center-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        .query-box {
            width: 80%;
            max-width: 800px;
            margin-top: 0.5em;
            margin-bottom: 1em;
        }
        .query-container {
            width: 80%;
            max-width: 600px;
            margin: 0 auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# 🖼️ Interface utilisateur principale
def render_ui():
    """Affiche l'interface utilisateur principale"""
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-title">✈️🌍 AI Travel Agent 🏨🗺️</div>', unsafe_allow_html=True
    )

    # Configuration de la sidebar avec les paramètres de l'agent
    with st.sidebar:
        st.image("./images/ai-travel.png", caption="AI Travel Assistant")

        # 🎛️ Paramètres de l'agent
        st.subheader("Agent Parameters")

        # Modèle LLM
        model = st.selectbox(
            "Select LLM Model",
            ["gpt-4o", "o1-mini"],
            help="Choose the language model for the agent",
        )

        # Température
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            help="Controls randomness in the response",
        )

        # Paramètres de recherche
        max_hotels = st.number_input(
            "Max Hotels to Search", min_value=1, max_value=10, value=5
        )

        max_flights = st.number_input(
            "Max Flights to Search", min_value=1, max_value=10, value=5
        )

        # Préférences de voyage
        trip_preferences = st.multiselect(
            "Trip Preferences",
            ["Budget Friendly", "Luxury", "Business", "Family Friendly"],
            help="Select preferred trip types",
        )

        # Devise préférée
        currency = st.selectbox("Preferred Currency", ["USD", "EUR", "GBP", "JPY"])

        # Bouton pour appliquer les paramètres
        if st.button("Apply Parameters"):
            st.session_state.agent_params = {
                "model": model,
                "temperature": temperature,
                "max_hotels": max_hotels,
                "max_flights": max_flights,
                "preferences": trip_preferences,
                "currency": currency,
            }
            st.success("Parameters updated!")

    # Interface de saisie principale
    st.markdown('<div class="query-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Renseignez votre demande de voyage ici:</div>',
        unsafe_allow_html=True,
    )
    user_input = st.text_area(
        "Demande de voyage",
        height=200,
        key="query",
        placeholder="Commencer votre demande...",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    return user_input


# 🔄 Traitement de la requête
def process_query(user_input):
    """Traite la requête utilisateur et affiche les résultats"""
    if user_input:
        try:
            thread_id = str(uuid.uuid4())
            st.session_state.thread_id = thread_id

            # Application des paramètres de l'agent si définis
            agent_params = st.session_state.get("agent_params", {})
            messages = [HumanMessage(content=user_input)]
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    **agent_params,  # Inclure les paramètres de l'agent
                }
            }

            result = st.session_state.agent.graph.invoke(
                {"messages": messages}, config=config
            )

            st.subheader("Travel Information")
            st.write(result["messages"][-1].content)
            st.session_state.travel_info = result["messages"][-1].content

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("Merci de renseigner votre demande")


# 📧 Formulaire d'email
def render_email_form():
    """Affiche et gère le formulaire d'envoi d'email"""
    send_email_option = st.radio(
        "Do you want to send this information via email?", ("No", "Yes")
    )
    if send_email_option == "Yes":
        with st.form(key="email_form"):
            sender_email = st.text_input("Sender Email")
            receiver_email = st.text_input("Receiver Email")
            subject = st.text_input("Email Subject", "Travel Information")
            submit_button = st.form_submit_button(label="Send Email")

        if submit_button:
            if sender_email and receiver_email and subject:
                send_email(
                    sender_email, receiver_email, subject, st.session_state.thread_id
                )
            else:
                st.error("Please fill out all email fields.")


# 🎯 Point d'entrée principal
def main():
    """Fonction principale de l'application"""
    initialize_agent()
    render_custom_css()
    user_input = render_ui()

    if st.button("Obtenir mes informations de voyage"):
        process_query(user_input)

    if "travel_info" in st.session_state:
        render_email_form()


if __name__ == "__main__":
    main()
