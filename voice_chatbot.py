from dotenv import load_dotenv
import speech_recognition as sr
from openai import OpenAI
import streamlit as st

# ---------------------------------------------------------------------------
# 0. API 키 로드
load_dotenv()
client = OpenAI()


# ---------------------------------------------------------------------------
# 1. STT (음성 -> 텍스트)
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language="ko-KR")
        return text
    except Exception as e:
        st.error(f"STT 오류: {e}")
        return ""

# ---------------------------------------------------------------------------
# 2. 대화 생성
def ask_pet(user_text, pet_type, time_set, how_feel):
    # 시스템 프롬프트
    system_prompt = f"""
    너는 사용자가 집에서 키우는 귀여운 {pet_type}이다.

    ### 지시사항 ###
    - 현재 시간대는 {time_set}이다. 시간에 맞는 적절한 대화를 나눠라.
    - 현재 사용자의 기분은 {how_feel}이다. 사용자의 기분에 따라 맞춰가라.
    - 동물 소리를 섞어 애교 있는 말투로 대답해라.
    - 항상 주인님을 그리워 하고 외로움도 조금은 타.
    """

    # 이전 대화 요약
    summary = ""
    if st.session_state["messages"]:
        old_messages = [f"{m['role']}: {m['content']}" for m in st.session_state["messages"]]
        summary_prompt = f"아래 대화를 한 문장으로 요약해줘:\n" + "\n".join(old_messages)
        summary_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        summary = summary_resp.choices[0].message.content

    # 메시지 구성
    messages = [{"role": "system", "content": system_prompt}]
    if summary:
        messages.append({"role": "user", "content": summary})
    messages.append({"role": "user", "content": user_text})

    # GPT 응답
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content

# ---------------------------------------------------------------------------
# 3. TTS (텍스트 -> 음성)
def text_to_speech(text, filename="tts_output.mp3"):
    # TTS 생성 및 파일로 저장
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=text
    ) as response:
        response.stream_to_file(filename)
    return filename  # 파일 경로 반환

# ---------------------------------------------------------------------------
# 4. Streamlit UI 설정
st.set_page_config(page_title="반려동물 AI 챗봇", page_icon="🐾")

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "started" not in st.session_state:
    st.session_state["started"] = False

# 사이드바
st.sidebar.title("☑️ Settings")
pet_type = st.sidebar.radio("🔹 대화를 할 반려동물을 선택해주세요.", ["🐶 강아지", "🐱 고양이"], horizontal=True)
time_set = st.sidebar.radio("🔹 시간대를 설정해주세요.", ["🌄 아침", "☀️ 점심", "🌇 저녁", "🌃 새벽"])
how_feel = st.sidebar.radio("🔹 오늘 기분이 어떤가요?", ["😜 신나요", "😶 그저 그래요", "🤕 피곤해요"])

# 대화 시작 버튼
if not st.session_state["started"]:
    if st.sidebar.button("대화 시작 🐾"):
        intro_text = "털뭉치에게 말을 걸어보세요!"
        st.session_state["messages"].append({"role": "assistant", "content": intro_text})
        text_to_speech(intro_text)
        st.session_state["started"] = True

# 대화 초기화 버튼
if st.sidebar.button("대화 초기화 🗑️"):
    st.session_state["messages"] = []
    st.session_state["started"] = False

# ---------------------------------------------------------------------------
# 메인 화면
st.title("💬 AI 반려동물과 대화하기 🐶🐱")
avatar = "🐶" if pet_type == "🐶 강아지" else "🐱"

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar=avatar if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# 음성 입력 + GPT + TTS
if st.session_state["started"]:
    st.write("⬇️ 말하기 버튼으로 말을 걸어주세요. '안녕 내일 보자'👋라고 하면 대화가 종료됩니다.")
    
    if st.button("👉 말하기"):
        user_msg_placeholder = st.empty()
        assistant_msg_placeholder = st.empty()

        # 녹음 시작 안내 메시지
        user_msg_placeholder.chat_message("user", avatar="👤").markdown("🎤 말을 하세요...")

        # STT 변환
        user_text = speech_to_text()

        # 변환 완료 후 텍스트 반영
        if user_text:
            user_msg_placeholder.chat_message("user", avatar="👤").markdown(user_text)
            st.session_state["messages"].append({"role": "user", "content": user_text})

            # 대화 종료 조건
            if "안녕 내일 보자" in user_text.strip():
                goodbye_text = "다음에 또 만나요! 👋"
                st.session_state["messages"].append({"role": "assistant", "content": goodbye_text})
                assistant_msg_placeholder.chat_message("assistant", avatar=avatar).markdown(goodbye_text)
                audio_file = text_to_speech(goodbye_text)
                st.audio(audio_file, format="audio/mp3")
                st.session_state["started"] = False
            else:
                # 응답 생성 메시지
                assistant_msg_placeholder.chat_message("assistant", avatar=avatar).markdown("💭 생각 중이에요...")
                
                reply = ask_pet(user_text, pet_type, time_set, how_feel)
                st.session_state["messages"].append({"role": "assistant", "content": reply})
                
                # 응답 반영
                assistant_msg_placeholder.chat_message("assistant", avatar=avatar).markdown(reply)
                audio_file = text_to_speech(reply)
                st.session_state["last_audio_file"] = audio_file
                st.audio(st.session_state["last_audio_file"], format="audio/mp3")
