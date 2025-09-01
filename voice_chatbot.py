from dotenv import load_dotenv
import speech_recognition as sr
from openai import OpenAI
import streamlit as st
import base64


# -----------------------------------------------------------------------------
# API 키 로드

load_dotenv()

# -----------------------------------------------------------------------------
# 1. STT (음성 -> 텍스트)

def speech_to_text():
    recognizer = sr.Recognizer()

    while True:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
            
        try:
            text = recognizer.recognize_google(audio, language="ko-KR")
            print("👤 User:", text)
            return text
        except Exception as e:
            print("❌ STT Error:", e)
            return ""
        
# -----------------------------------------------------------------------------
# 2. 프롬프트 엔지니어링

client = OpenAI()   

def ask_pet(user_text, pet_type, time_set, how_feel):

    system_prompt = f'''
        너는 사용자가 집에서 키우는 귀여운 {pet_type}이다. 
        현재 시간대는 {time_set}, 사용자의 기분은 {how_feel}.
        동물 소리를 섞어 애교 있는 말투로 사용자와 대화해라.
        '''

    # 1. 이전 대화를 문자열로 합치기
    if st.session_state["messages"]:
        old_messages = []
        for m in st.session_state["messages"]:
            old_messages.append(f"{m['role']}: {m['content']}")
        old_messages_text = "\n".join(old_messages)

        # 2. 이전 대화 요약
        summary_prompt = f"아래 대화를 한 문장으로 요약해줘:\n{old_messages_text}"
        summary = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}]
        ).choices[0].message.content
    else:
        summary = ""

    # 3. 요약 + 이번 사용자 입력을 모델에 전달
    messages = [{"role": "system", "content": system_prompt}]
    if summary:
        messages.append({"role": "user", "content": summary})
    messages.append({"role": "user", "content": user_text})

    # 4. 모델 호출
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    # 5. 결과 기록
    reply = response.choices[0].message.content
    st.session_state["messages"].append({"role": "user", "content": user_text})
    st.session_state["messages"].append({"role": "assistant", "content": reply})

    return reply

# -----------------------------------------------------------------------------
# 3. TTS (텍스트 -> 음성)

def text_to_speech(text):
    with client.audio.speech.with_streaming_response.create(
        model='tts-1',
        voice='nova',
        input=text
    ) as response:
        audio_bytes = response.read()

    # 자동 재생 오디오 태그 삽입
    audio_base64 = base64.b64encode(audio_bytes).decode()
    audio_html = f"""
        <audio autoplay="true">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. streamlit 페이지 구현

st.set_page_config(page_title="반려동물 AI 챗봇", page_icon="🐾")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "started" not in st.session_state:
    st.session_state["started"] = False

# 사이드바 설정
st.sidebar.title("☑️Settings")
pet_type = st.sidebar.radio("🔹대화를 할 반려동물을 선택해주세요.", ["🐶 강아지", "🐱 고양이"], horizontal=True)
time_set = st.sidebar.radio("🔹시간대를 설정해주세요.", ["🌅 아침", "🌞 점심", "🌃 저녁", "🌝 새벽"])
how_feel = st.sidebar.radio("🔹오늘 기분이 어떤가요?", ["😜 신나요", "😶 그저 그래요", "🤕 피곤해요"])

# 대화 시작 버튼
if not st.session_state["started"]:
    if st.sidebar.button("대화 시작🐾"):
        # 안내 멘트
        intro_text = "털뭉치에게 말을 걸어보세요!"
        
        # 세션에 기록
        st.session_state["messages"].append({"role": "assistant", "content": intro_text})
        
        # TTS로 재생
        text_to_speech(intro_text)
        
        st.session_state["started"] = True

# 대화 초기화 버튼
if st.sidebar.button("대화 초기화🗑️"):
    st.session_state["messages"] = []
    st.session_state["started"] = False


# 메인 화면
st.title("💬 AI 반려동물과 대화하기 🐾")

# 채팅창 출력        
avatar = "🐶" if pet_type == "🐶 강아지" else "🐱"

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar=avatar if msg["role"] == "assistant" else "🙂"):
        st.markdown(msg["content"])


# 음성 입력 루프 (버튼 클릭 후 활성화)
if st.session_state["started"]:
    st.write("🎤 마이크로 말을 걸어주세요. '안녕 내일 보자'👋라고 하면 대화가 종료됩니다.")
    
    user_text = speech_to_text()
    
    if user_text:
        if user_text == "안녕 내일 보자":
            st.session_state["messages"].append({"role": "user", "content": user_text})
            st.session_state["messages"].append({"role": "assistant", "content": "다음에 또 만나요! 👋"})
            text_to_speech("다음에 또 만나요! 👋")
            st.session_state["started"] = False
        else:
            reply = ask_pet(user_text, pet_type, time_set, how_feel)
            text_to_speech(reply)

# -----------------------------------------------------------------------------