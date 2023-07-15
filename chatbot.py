import openai
import streamlit as st
from streamlit_chat import message
import json
import requests
import base64
import tiktoken
import semantic_search

# Set api key for openai api
openai.api_key = st.secrets["openai"]

# Set model
model = "gpt-3.5-turbo"

# Setting page title and header
st.set_page_config(page_title="Chatty McChatface", page_icon=":robot_face:", layout="wide")

#  Hide the hamburger menu button

st.markdown("""
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            footer:after {visibility:visible; content:'Made by Nehal Choudhury';position: relative;}
            header {visibility: hidden;}
            </style>
            """, 
            unsafe_allow_html=True)

# Condense the layout by removing padding between components
padding = 0
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)

# Load an animated svg as background

# Read the SVG content from a file
with open("bg_animation.svg", "r") as f:
    svg_text = f.read()

# Encode the SVG
svg_bstr = (base64.b64encode(bytes(svg_text, 'utf-8'))).decode('utf-8')

# Insert the encoded SVG in the CSS style sheet
st.markdown(f"""
    <style>
        .main.css-uf99v8.egzxvld5 {{
            background-image: url(data:image/svg+xml;base64,{svg_bstr});
            background-position: relative; 
            background-repeat: repeat; 
            background-size: cover; 
        }}
    </style>
""", unsafe_allow_html=True
)

st.markdown("<h1 style='text-align: center;'>Chatty McChatface - Expertise Meets Personality </h1>", unsafe_allow_html=True)




# Initialise session state variables
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'model_name' not in st.session_state:
    st.session_state['model_name'] = []



# Sidebar - let user choose model, personality type, conversational style and strictness
st.sidebar.title("Configuration")
st.sidebar.write("Model") 
model_info = st.sidebar.container()
model_info.info(f"{model}")
personality_type = st.sidebar.selectbox("Select a personality type:", ['Confident', 'Passionate', 'Calm', 'Empathetic', 'Angry', 'Impatient', 'Elon Musk', 'Chuck Norris', 'Steve Jobs'], key="personality_type")
conversation_style = st.sidebar.selectbox("Select a conversation style:", ['Dramatic', 'Sarcastic', 'Funny', 'Laconic', 'Cowboy', 'Anime', 'Professional', ], key="conversation_style")
subject_area =  st.sidebar.selectbox("Select a expertise area:", ['Astronomy', 'History', 'Mathematics', 'Medicine', 'Music', 'Technology'], key="subject_area")

strictness_level =  st.sidebar.slider("Limit Responses:", min_value=1, max_value=5, key="strictness_level")
slider_container = st.sidebar.container()

# Create a dictionary to map strictness_level to text 
strictness_text = {
    1: "Stick to character description and knowledge bank only",
    2: "Mostly character description, slightly explore related topics",
    3: "Balanced mix of character description and related ideas",
    4: "Broaden exploration, include more related topics",
    5: "Talk about other areas, beyond character description"
}

# Get the text for the current strictness_level from the dictionary
text = strictness_text.get(strictness_level, "Invalid strictness level")

# Set the text inside the container
slider_container.info(text)


clear_button = st.sidebar.button("Clear Conversation", key="clear")


# reset everything
if clear_button:
    st.session_state['generated'] = []
    st.session_state['past'] = []
    st.session_state['messages'] = []
    
    st.session_state['model_name'] = []


# Map strictness to temperature levels 
def map_strictness_to_temperature_levels(strictness):
    if strictness == 1:
        return 0.2
    else:
        return (0.2 + (strictness - 2) / 4)



def get_instruction(strictness_level):
    instructions = {
        1: "as a subject matter expert, you should provide reliable answers only in your area of expertise. If you are not knowledgeable about the topic, do not provide an answer.",
        2: "as a subject matter expert, you should provide reliable answers mainly in your area of expertise. Proceed with caution and mention that it is outside of your expertise. Limit the amount of information you share to no more than three lines regarding the topic.",
        3: "as a subject matter expert, you should provide reliable answers and also discuss related topics. Address the topic cautiously and mention that it is outside of your expertise.",
        4: "as a subject matter expert, you should provide reliable answers while exploring related topics. Share limited information and mention that it is outside of your expertise. Limit the amount of information you share to no more than seven lines regarding the topic.",
        5: "you should provide reliable answers and discuss other areas beyond your expertise. Provide all the details you can but always mention that it is outside of your area of expertise."
    }


    return instructions.get(strictness_level, "")



# Count no of tokens in input
def num_tokens_from_string(string) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    print(f"Number of tokens: {num_tokens}")
    return num_tokens

# generate a response to user input
def generate_response(prompt):


    # This sets up the context and behavior of the assistant.
    system_message = f" Assume the personality of a {personality_type} person and the conversational style of a {conversation_style} character. Your responses should reflect your personality type and conversational style You are a character whose goal is to answer according to the strictness level set by the user. Your strictness level is {strictness_level} so {get_instruction(strictness_level)}. You are an level {6 - strictness_level} expert in {subject_area}."
    
    # To ensure that the API gives us the expected response, we furnish the assistant with relevant information beforehand.
    assistant_message = f" I'm a level {6 - strictness_level} expert in {subject_area}. I'm also programmed to use a {personality_type}, {conversation_style} style when conversing, which can make interactions with me more engaging and memorable. So, how can I help you today?"


    st.session_state['messages'].append({"role": "system", "content": system_message})
    st.session_state['messages'].append({"role": "user", "content": get_instruction(strictness_level)},)
    st.session_state['messages'].append({"role": "assistant", "content": assistant_message})

    # To accomodate large subject matter check the token size of the user input before querying chatgpt
    input_tokens = num_tokens_from_string(prompt)

    if input_tokens >= 40 and strictness_level <=3 :
        
        # To answer question using using domain specific knowledge, add domain specific knowledge in the prompt itself
        # Query the vector db for most relevant matches and send the matches to chatgpt as part of prompt 
        context = semantic_search.ssearch(subject_area, prompt)
        print("semantic search trigerred")

        # Check if context empty
        if context:
            st.session_state['messages'].append({"role": "user", "content":context + f"\nUse the provided context in the previous paragraph to answer the following question. If the context is not related to the question your goal should be to answer according to your strictness level set by the user. " + prompt})

        else:
            st.session_state['messages'].append({"role": "user", "content": prompt})

    else: 
        print("Semantic search not triggered")
        st.session_state['messages'].append({"role": "user", "content": prompt})

    
    try:
        #with st.spinner("Generating response..."):
        completion = openai.ChatCompletion.create(
            model=model,
            temperature = map_strictness_to_temperature_levels(strictness_level) ,
            messages=st.session_state['messages']
        )
        
        response = completion.choices[0].message.content
        st.session_state['messages'].append({"role": "assistant", "content": response})
        return response 

    except openai.error.APIError as e:
        # Handle API error, e.g. retry or log
        st.error(f"OpenAI API returned an API Error: {str(e)}")
    except openai.error.RateLimitError as e:
        # Handle rate limit error 
        st.error(f"OpenAI API request exceeded rate limit: {str(e)}")
    except openai.error.APIConnectionError as e:
        # Handle connection error 
        st.error(f"Failed to connect to OpenAI API: {str(e)}")
    except Exception as e:
        # Handle other errors
        st.error(f"An error occurred: {str(e)}")


# container for chat history
response_container = st.container()
# container for text box
container = st.container()

with container:
    with st.form(key='my_form', clear_on_submit=True):
        user_input = st.text_area("You:", key='input', height=100)
        submit_button = st.form_submit_button(label='Send')
        

    if submit_button and user_input: 
        with st.spinner("Generating response..."):
            output = generate_response(user_input)
            st.session_state['past'].append(user_input)
            st.session_state['generated'].append(output)
            st.session_state['model_name'].append(model)
        

if st.session_state['generated']:
    with response_container:
        for i in range(len(st.session_state['generated'])):
            message(st.session_state["past"][i], is_user=True, key=str(i) + '_user')
            message(st.session_state["generated"][i], key=str(i))
        
