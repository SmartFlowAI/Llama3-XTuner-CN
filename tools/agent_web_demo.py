import copy
import hashlib
import json
import os
import sys

import streamlit as st

from lagent.actions import ActionExecutor, ArxivSearch, FinishAction
from lagent.agents.react import CALL_PROTOCOL_EN, FORCE_STOP_PROMPT_EN, ReAct, ReActProtocol
from lagent.llms import HFTransformerCasualLM
from lagent.schema import AgentStatusCode


LLAMA3_META = [
    dict(
        role='system',
        begin='<|start_header_id|>system<|end_header_id|>\n\n',
        end='<|eot_id|>'),
    dict(
        role='user',
        begin='<|start_header_id|>user<|end_header_id|>\n\n',
        end='<|eot_id|>'),
    dict(
        role='assistant',
        begin='<|start_header_id|>assistant<|end_header_id|>\n\n',
        end='<|eot_id|>'),
]


class SessionState:

    def init_state(self):
        """Initialize session state variables."""
        st.session_state['assistant'] = []
        st.session_state['user'] = []

        action_list = [
            ArxivSearch(),
        ]
        st.session_state['plugin_map'] = {
            action.name: action
            for action in action_list
        }
        st.session_state['model_map'] = {}
        st.session_state['model_selected'] = None
        st.session_state['plugin_actions'] = set()
        st.session_state['history'] = []

    def clear_state(self):
        """Clear the existing session state."""
        st.session_state['assistant'] = []
        st.session_state['user'] = []
        st.session_state['model_selected'] = None
        st.session_state['file'] = set()
        if 'chatbot' in st.session_state:
            st.session_state['chatbot']._session_history = []


class StreamlitUI:

    def __init__(self, session_state: SessionState, model_path: str):
        self.init_streamlit()
        self.session_state = session_state
        self.model_path = model_path

    def init_streamlit(self):
        """Initialize Streamlit's UI settings."""
        st.set_page_config(
            layout='wide',
            page_title='lagent-web',
            page_icon='./docs/imgs/lagent_icon.png')
        st.header(':robot_face: :blue[Lagent] Web Demo ', divider='rainbow')
        st.sidebar.title('模型控制')
        st.session_state['file'] = set()
        st.session_state['model_path'] = None

    def setup_sidebar(self):
        """Setup the sidebar with the available models."""
        model_name = st.sidebar.text_input('模型名称：', value='LLaMA-3-8B-Instruct')
        call_protocol = st.sidebar.text_area('调用协议提示：', value=CALL_PROTOCOL_EN)
        force_stop = st.sidebar.text_area(
            '强制停止提示：', value=FORCE_STOP_PROMPT_EN)
        model_path = st.sidebar.text_input(
            '模型路径：', value=self.model_path)
        if model_name != st.session_state['model_selected'] or st.session_state[
                'model_path'] != model_path:
            st.session_state['model_path'] = model_path
            model = self.init_model(model_name, model_path)
            self.session_state.clear_state()
            st.session_state['model_selected'] = model_name
            if 'chatbot' in st.session_state:
                del st.session_state['chatbot']
        else:
            model = st.session_state['model_map'][model_name]

        plugin_name = st.sidebar.multiselect(
            '插件选择',
            options=list(st.session_state['plugin_map'].keys()),
            default=[],
        )
        plugin_action = [
            st.session_state['plugin_map'][name] for name in plugin_name
        ]
        # 保证一定有 FinishAction 以输出
        plugin_action.append(FinishAction())

        if 'chatbot' in st.session_state:
            if len(plugin_action) > 0:
                st.session_state['chatbot']._action_executor = ActionExecutor(
                    actions=plugin_action)
            else:
                st.session_state['chatbot']._action_executor = None
            st.session_state['chatbot']._protocol.call_protocol = call_protocol
            st.session_state['chatbot']._protocol.force_stop = force_stop
        if st.sidebar.button('清空对话', key='clear'):
            self.session_state.clear_state()
        uploaded_file = st.sidebar.file_uploader('上传文件')

        return model_name, model, plugin_action, uploaded_file, model_path

    def init_model(self, model_name, path):
        """Initialize the model based on the input model name."""
        st.session_state['model_map'][model_name] = HFTransformerCasualLM(
            path=path,
            meta_template=LLAMA3_META,
            max_new_tokens=1024,
            top_p=0.8,
            top_k=None,
            temperature=0.1,
            repetition_penalty=1.0,
            stop_words=['<|eot_id|>'])
        return st.session_state['model_map'][model_name]

    def initialize_chatbot(self, model, plugin_action):
        """Initialize the chatbot with the given model and plugin actions."""
        return ReAct(
            llm=model,
            action_executor=None,
            protocol=ReActProtocol(),
            max_turn=7)

    def render_user(self, prompt: str):
        with st.chat_message('user'):
            st.markdown(prompt)

    def render_assistant(self, agent_return):
        with st.chat_message('assistant'):
            for action in agent_return.actions:
                if (action) and (action.type != 'FinishAction'):
                    self.render_action(action)
            st.markdown(agent_return.response)

    def render_plugin_args(self, action):
        action_name = action.type
        args = action.args
        import json
        parameter_dict = dict(name=action_name, parameters=args)
        parameter_str = '```json\n' + json.dumps(
            parameter_dict, indent=4, ensure_ascii=False) + '\n```'
        st.markdown(parameter_str)

    def render_interpreter_args(self, action):
        st.info(action.type)
        st.markdown(action.args['text'])

    def render_action(self, action):
        st.markdown(action.thought)
        if action.type == 'IPythonInterpreter':
            self.render_interpreter_args(action)
        elif action.type == 'FinishAction':
            pass
        else:
            self.render_plugin_args(action)
        self.render_action_results(action)

    def render_action_results(self, action):
        """Render the results of action, including text, images, videos, and
        audios."""
        if (isinstance(action.result, dict)):
            if 'text' in action.result:
                st.markdown('```\n' + action.result['text'] + '\n```')
            if 'image' in action.result:
                # image_path = action.result['image']
                for image_path in action.result['image']:
                    image_data = open(image_path, 'rb').read()
                    st.image(image_data, caption='Generated Image')
            if 'video' in action.result:
                video_data = action.result['video']
                video_data = open(video_data, 'rb').read()
                st.video(video_data)
            if 'audio' in action.result:
                audio_data = action.result['audio']
                audio_data = open(audio_data, 'rb').read()
                st.audio(audio_data)
        elif isinstance(action.result, list):
            for item in action.result:
                if item['type'] == 'text':
                    st.markdown('```\n' + item['content'] + '\n```')
                elif item['type'] == 'image':
                    image_data = open(item['content'], 'rb').read()
                    st.image(image_data, caption='Generated Image')
                elif item['type'] == 'video':
                    video_data = open(item['content'], 'rb').read()
                    st.video(video_data)
                elif item['type'] == 'audio':
                    audio_data = open(item['content'], 'rb').read()
                    st.audio(audio_data)
        if action.errmsg:
            st.error(action.errmsg)


def main(model_path):
    # logger = get_logger(__name__)
    # Initialize Streamlit UI and setup sidebar
    if 'ui' not in st.session_state:
        session_state = SessionState()
        session_state.init_state()
        st.session_state['ui'] = StreamlitUI(session_state, model_path)

    else:
        st.set_page_config(
            layout='wide',
            page_title='lagent-web',
            page_icon='./docs/imgs/lagent_icon.png')
        st.header(':robot_face: :blue[Lagent] Web Demo ', divider='rainbow')
    _, model, plugin_action, uploaded_file, _ = st.session_state[
        'ui'].setup_sidebar()

    # Initialize chatbot if it is not already initialized
    # or if the model has changed
    if 'chatbot' not in st.session_state or model != st.session_state[
            'chatbot']._llm:
        st.session_state['chatbot'] = st.session_state[
            'ui'].initialize_chatbot(model, plugin_action)
        st.session_state['session_history'] = []

    for prompt, agent_return in zip(st.session_state['user'],
                                    st.session_state['assistant']):
        st.session_state['ui'].render_user(prompt)
        st.session_state['ui'].render_assistant(agent_return)

    if user_input := st.chat_input(''):
        with st.container():
            st.session_state['ui'].render_user(user_input)
        st.session_state['user'].append(user_input)
        # Add file uploader to sidebar
        if (uploaded_file
                and uploaded_file.name not in st.session_state['file']):

            st.session_state['file'].add(uploaded_file.name)
            file_bytes = uploaded_file.read()
            file_type = uploaded_file.type
            if 'image' in file_type:
                st.image(file_bytes, caption='Uploaded Image')
            elif 'video' in file_type:
                st.video(file_bytes, caption='Uploaded Video')
            elif 'audio' in file_type:
                st.audio(file_bytes, caption='Uploaded Audio')
            # Save the file to a temporary location and get the path

            postfix = uploaded_file.name.split('.')[-1]
            # prefix = str(uuid.uuid4())
            prefix = hashlib.md5(file_bytes).hexdigest()
            filename = f'{prefix}.{postfix}'
            file_path = os.path.join(root_dir, filename)
            with open(file_path, 'wb') as tmpfile:
                tmpfile.write(file_bytes)
            file_size = os.stat(file_path).st_size / 1024 / 1024
            file_size = f'{round(file_size, 2)} MB'
            # st.write(f'File saved at: {file_path}')
            user_input = [
                dict(role='user', content=user_input),
                dict(
                    role='user',
                    content=json.dumps(dict(path=file_path, size=file_size)),
                    name='file')
            ]
        if isinstance(user_input, str):
            user_input = [dict(role='user', content=user_input)]
        st.session_state['last_status'] = AgentStatusCode.SESSION_READY
        agent_return = st.session_state['chatbot'].chat(
            st.session_state['session_history'] + user_input)
        if agent_return.state == AgentStatusCode.END:
            st.session_state['ui'].render_assistant(agent_return)
        st.session_state['session_history'] += (
            user_input + agent_return.inner_steps)
        st.session_state['assistant'].append(copy.deepcopy(agent_return))
        st.session_state['last_status'] = agent_return.state


if __name__ == '__main__':
    model_path = sys.argv[1]
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.join(root_dir, 'tmp_dir')
    os.makedirs(root_dir, exist_ok=True)
    main(model_path)
