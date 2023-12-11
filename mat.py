import streamlit as st
import base64
import pyaudio
import numpy as np
from datetime import datetime
import openpyxl
import speech_recognition as sr

# ChatGPT API Configuration
api_url = "https://api.openai.com/v1/chat/completions"
api_key = "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"  # Reemplaza con tu clave de API de OpenAI

# PyAudio configuration
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=22050,
                input=True,
                frames_per_buffer=8192)

# Streamlit sesion configuration
st.title("Grabación y Transcripción de Audio con ChatGPT")

# Function to transcript the audio using the APY ChatGPT
def transcribe_audio(audio_data):
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": audio_data},
        ],
        "model": "text-davinci-003",
    }

    response_json = {}  # Initialize variable outside of try block

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()  # This will throw an exception if the request was not successful
        response_json = response.json()
        query = response_json["choices"][0]["message"]["content"]
        return query
    except requests.exceptions.HTTPError as errh:
        print(f"Error HTTP: {errh}")
        return ""
    except requests.exceptions.ConnectionError as errc:
        print(f"Error de conexión: {errc}")
        return ""
    except requests.exceptions.Timeout as errt:
        print(f"Error de tiempo de espera: {errt}")
        return ""
    except requests.exceptions.RequestException as err:
        print(f"Error de solicitud: {err}")
        print(f"Respuesta JSON completa: {response_json}")
        return ""

def record_command():
    recognizer = sr.Recognizer()

    st.write("Esperando comandos: Resumen o Acciones...")

    try:
        with sr.Microphone() as source:
            audio_data = recognizer.listen(source, timeout=20)

        command = recognizer.recognize_google(audio_data).lower()
        return command
    except sr.UnknownValueError:
        return ""

def create_excel(resumen_text, accion_list):
    # Function to create an Excel file and write the data
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Minuta'

    if resumen_text:
        ws.append(['Resumen'])
        ws.append([resumen_text])

    if accion_list:
        ws.append(['ID', 'Acción', 'Responsable', 'Fecha'])
        for idx, accion in enumerate(accion_list, start=1):
            ws.append([idx, accion['accion'], accion['responsable'], accion['fecha']])

    wb.save('minuta.xlsx')

# Botón para iniciar la grabación de la minuta
if st.button("Minuta"):
    st.session_state.recording = True
    st.session_state.resumen_audio = []

    while st.session_state.recording:
        command = record_command()

        if command == "resumen":
            st.write("Starting speech recognition for summary. Say 'done' to finish.")
            st.session_state.resumen_audio = []

            while True:
                try:
                    audio_chunk = stream.read(8192)
                    st.session_state.resumen_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))
                except IOError as e:
                    st.error(f"Error al leer audio: {e}")
                except Exception as e:
                    st.error(f"Error inesperado al leer audio: {e}")

                command = record_command()
                if command == "done":
                    resumen_text = transcribe_audio(np.concatenate(st.session_state.resumen_audio[:-1]))
                    create_excel(resumen_text, None)
                    st.session_state.recording = False
                    break

                if command == "acciones":
                    break

        elif command == "acciones":
            st.write("Starting speech recognition for actions. Say 'done' to end each action.")
            st.session_state.resumen_audio = []
            accion_list = []

            while True:
                # Record the action
                st.write("Please say the action. Say 'done' to finish.")
                accion_audio = record_command()
                while True:
                    audio_chunk = stream.read(8192)
                    accion_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    command = record_command()
                    if command == "done":
                        break

                # Record the person responsible
                st.write("Now, say the person responsible. Say 'done' to finish.")
                responsable_audio = record_command()
                while True:
                    audio_chunk = stream.read(8192)
                    responsable_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    command = record_command()
                    if command == "done":
                        break

                # Record the date
                st.write("Finally, give the date in DD/MM/YYYY format. Say 'done' to finish.")
                fecha_audio = record_command()
                while True:
                    audio_chunk = stream.read(8192)
                    fecha_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    command = record_command()
                    if command == "done":
                        break

                # Convert date to an Excel date format
                fecha_excel = datetime.now().strftime("%Y-%m-%d")
                try:
                    fecha_excel = datetime.strptime(transcribe_audio(np.concatenate(fecha_audio[:-1])), "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    pass

                accion_list.append({
                    'accion': transcribe_audio(np.concatenate(accion_audio[:-1])),
                    'responsable': transcribe_audio(np.concatenate(responsable_audio[:-1])),
                    'fecha': fecha_excel
                })

                st.write("Ready for the next action? Say 'done' or 'end' to finish.")

                siguiente_audio = record_command()
                while True:
                    audio_chunk = stream.read(8192)
                    siguiente_audio.append(np.frombuffer(audio_chunk, dtype=np.int16))

                    command = record_command()
                    if command == "fin":
                        break

                    if command == "listo":
                        break

                if command == "fin":
                    break

            create_excel(None, accion_list)
            st.session_state.recording = False

# Closing the stream and PyAudio on closing
st.text("Cerrando la transmisión y PyAudio al cerrar la aplicación.")
stream.stop_stream()
stream.close()
p.terminate()
