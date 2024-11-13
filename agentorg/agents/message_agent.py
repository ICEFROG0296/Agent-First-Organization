import logging

from langgraph.graph import StateGraph, START
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from agentorg.agents.agent import BaseAgent, register_agent
from agentorg.agents.prompts import message_generator_prompt, message_flow_generator_prompt
from agentorg.utils.utils import chunk_string
from agentorg.utils.graph_state import MessageState
from agentorg.utils.model_config import MODEL


logger = logging.getLogger(__name__)


@register_agent
class MessageAgent(BaseAgent):

    description = "The agent that used to deliver the message to the user, either a question or provide some information."

    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(model="gpt-4o", timeout=30000)
        self.action_graph = self._create_action_graph()

    def generator(self, state: MessageState) -> MessageState:
        # get the input message
        user_message = state['user_message']
        orchestrator_message = state['orchestrator_message']
        message_flow = state['message_flow']

        # get the orchestrator message content
        orch_msg_content = orchestrator_message.message
        orch_msg_attr = orchestrator_message.attribute
        direct_response = orch_msg_attr.get('direct_response', False)
        if direct_response:
            return orch_msg_content
        
        if message_flow:
            prompt = PromptTemplate.from_template(message_flow_generator_prompt)
            input_prompt = prompt.invoke({"message": orch_msg_content, "formatted_chat": user_message.history, "initial_response": message_flow})
        else:
            prompt = PromptTemplate.from_template(message_generator_prompt)
            input_prompt = prompt.invoke({"message": orch_msg_content, "formatted_chat": user_message.history})
        logger.info(f"Prompt: {input_prompt.text}")
        chunked_prompt = chunk_string(input_prompt.text, tokenizer=MODEL["tokenizer"], max_length=MODEL["context"])
        final_chain = self.llm | StrOutputParser()
        answer = final_chain.invoke(chunked_prompt)

        state["message_flow"] = answer
        return state

    def _create_action_graph(self):
        workflow = StateGraph(MessageState)
        # Add nodes for each agent
        workflow.add_node("generator", self.generator)
        # Add edges
        workflow.add_edge(START, "generator")
        return workflow

    def execute(self, msg_state: MessageState):
        graph = self.action_graph.compile()
        result = graph.invoke(msg_state)
        return result


# if __name__ == "__main__":
#     user_message = ConvoMessage(history="", message="How can you help me?")
#     orchestrator_message = OrchestratorMessage(message="What is your name?", attribute={"direct_response": False})
#     agent = MessageAgent(user_message=user_message, orchestrator_message=orchestrator_message)
#     result = agent.execute()
#     print(result)
