import json
import audioop
import io
import wave
import os

import chainlit as cl
import numpy as np

from promptflow.client import load_flow
from openai import OpenAI

from typing import Optional

SILENCE_THRESHOLD = 3500
SILENCE_TIMEOUT = 1300.0
DATA_DIRECTORY = "data/source_documents/"

flow_path = "./parliament-ai-flow"
f = load_flow(flow_path)

data_source_path_list = [os.path.join(root, file) 
                         for root, dirs, files in os.walk(DATA_DIRECTORY) 
                         for file in files if file.endswith('.pdf')]

client = OpenAI()

@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.User]:
  # Fetch the user matching username from your database
  # and compare the hashed password with the value stored in the database
  if (username, password) == ("admin", "admin"):
    return cl.User(identifier="admin", metadata={"role": "admin", "provider": "credentials"})
  else:
    return None

@cl.step(type="tool")
async def speech_to_text(audio_file):
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text"
    )

    return response

@cl.on_chat_start
def start_chat():
    print("starting chat")

    cl.user_session.set(
        "chat_history",
        []
    )

@cl.set_starters
async def starters():
    return [
        cl.Starter(
            label="Digital Economy Policy for Data Centre",
            message="Give me main point for malaysia digital economy policy focusing in data centre",
        ),
        cl.Starter(
            label="Latest News Digital Economy Policy",
            message="What is 5 latest news about Malaysian digital economy?"
        )

    ]

@cl.step(type="llm")
async def call_promptflow(text, chat_history):

    response = await cl.make_async(f)(text=text, chat_history=chat_history)

    return response

@cl.on_audio_start
async def on_audio_start():

    cl.user_session.set("silent_duration_ms", 0)
    cl.user_session.set("is_speaking", False)
    cl.user_session.set("audio_chunks", [])

    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    
    audio_chunks = cl.user_session.get("audio_chunks")

    if audio_chunks is not None:
        audio_chunk = np.frombuffer(chunk.data, dtype=np.int16)
        audio_chunks.append(audio_chunk)
    
    if chunk.isStart:
        cl.user_session.set("last_elapsed_time", chunk.elapsedTime)
        cl.user_session.set("is_speaking", True)
        return
    
    audio_chunks = cl.user_session.get("audio_chunks")
    last_elapsed_time = cl.user_session.get("last_elapsed_time")
    silent_duration_ms = cl.user_session.get("silent_duration_ms")
    is_speaking = cl.user_session.get("is_speaking")

    # Calculate the time difference between this chunk and the previous one
    time_diff_ms = chunk.elapsedTime - last_elapsed_time
    cl.user_session.set("last_elapsed_time", chunk.elapsedTime)

    # Compute the RMS (root mean square) energy of the audio chunk
    audio_energy = audioop.rms(chunk.data, 2)  # Assumes 16-bit audio (2 bytes per sample)

    if audio_energy < SILENCE_THRESHOLD:
        # Audio is considered silent
        silent_duration_ms += time_diff_ms
        cl.user_session.set("silent_duration_ms", silent_duration_ms)
        if silent_duration_ms >= SILENCE_TIMEOUT and is_speaking:
            cl.user_session.set("is_speaking", False)
            await process_audio()
    else:
        cl.user_session.set("silent_duration_ms", 0)
        if not is_speaking:
            cl.user_session.set("is_speaking", True)

async def process_audio():

    if audio_chunks:=cl.user_session.get("audio_chunks"):
        
        concatenated = np.concatenate(list(audio_chunks))
        
        # Create an in-memory binary stream
        wav_buffer = io.BytesIO()
        
        # Create WAV file with proper parameters
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav_file.setframerate(24000)  # sample rate (24kHz PCM)
            wav_file.writeframes(concatenated.tobytes())
        
        # Reset buffer position
        wav_buffer.seek(0)
        
        cl.user_session.set("audio_chunks", [])

    frames = wav_file.getnframes()
    rate = wav_file.getframerate()

    duration = frames / float(rate)  
    if duration <= 1.71:
        print("The audio is too short, please try again.")
        return

    audio_buffer = wav_buffer.getvalue()

    input_audio_el = cl.Audio(content=audio_buffer, mime="audio/wav")

    whisper_input = ("audio/wav", audio_buffer, "audio/wav")
    transcription = await speech_to_text(whisper_input)

    await cl.Message(
        author="You",
        type="user_message",
        content=transcription,
        elements=[input_audio_el]
    ).send()

    chat_history = cl.user_session.get("chat_history")

    response = await call_promptflow(transcription, chat_history)

    answer = json.loads(response['output']['answer'])
    # Here, 'message' is a dictionary with 'assistant_name' and 'message_content'
    async with cl.Step(name="generate_result") as child_step:
        # Set the output of the step to the content of the message
        child_step.output = response

    await cl.Message(content=answer,
                     author="Answer").send()

    chat_history.append({"inputs": {"question": transcription}, 
                        "outputs": {"answer": answer}})

@cl.on_message
async def main(message: cl.Message):
    question = message.content
    chat_history = cl.user_session.get("chat_history")

    response = await call_promptflow(message.content, chat_history)

    try:
        function_call_status = response['main_agent_output']['function_call']['name']
    except:
        function_call_status = None
    
    if function_call_status in ['get_policy_database', 'get_latest_news']:
        
        answer = json.loads(response['output'])['answer']

    elif function_call_status in ['write_to_microsoft_word']:

        citation = response['function_call_output']
        answer = f"Your file are generated at {citation}"

    elif function_call_status in ['create_email_draft']:

        answer = "Your email draft has been generated"
    
    else:
        answer = json.loads(response['output'])['answer']
    
    try:
        # Remove the square brackets from the answer
        answer = answer.replace('[', '').replace(']', '')
    except:
        pass

    # Here, 'message' is a dictionary with 'assistant_name' and 'message_content'
    async with cl.Step(name="generate_result") as child_step:
        # Set the output of the step to the content of the message
        child_step.output = response

    elements = []
    #generate pdf element for each citation
    
    if function_call_status == 'get_policy_database':
        
        try:
            citations = json.loads(response['output'])['citations']

            for citation in citations:
                if ".pdf" in citation.lower():

                    file_path = [path for path in data_source_path_list if citation.lower() in path.lower()][0]

                    pdf_element = cl.Pdf(
                        name=citation,
                        display="side",
                        path=file_path,
                        page=1
                    )
                    elements.append(pdf_element)
        except:
            pass

    if function_call_status == 'write_to_microsoft_word':
        
        try: 
            docx_element = cl.File(
                name=citation,
                display="side",
                path=citation
                )
            elements.append(docx_element)
        except:
            pass
    
    await cl.Message(content=answer,
                     author="Answer", 
                     elements= elements).send()

    chat_history.append({"inputs": {"question": question}, 
                        "outputs": {"answer": answer}})
