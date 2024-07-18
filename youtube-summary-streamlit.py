import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator
import yt_dlp
import base64
from datetime import datetime

def get_video_id(url):
    if "youtu.be" in url:
        return url.split("/")[-1]
    elif "youtube.com" in url:
        return url.split("v=")[1].split("&")[0]
    else:
        return None

def get_video_info(url):
    try:
        ydl_opts = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        return {
            "title": info['title'],
            "description": info['description'],
            "views": info['view_count'],
            "length": info['duration'],
            "publish_date": datetime.strptime(info['upload_date'], "%Y%m%d").strftime("%Y년 %m월 %d일"),
            "channel_name": info['uploader'],
            "likes": info.get('like_count', '비공개'),
            "dislikes": info.get('dislike_count', '비공개')
        }
    except Exception as e:
        st.error(f"동영상 정보 가져오기 오류: {str(e)}")
        return None

def get_transcript(video_id, target_language):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[target_language])
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            original_text = " ".join([entry['text'] for entry in transcript])
            translator = GoogleTranslator(source='auto', target=target_language)
            translated_text = translator.translate(original_text)
            return translated_text
        except Exception as inner_e:
            st.error(f"자막 가져오기 오류: {str(inner_e)}")
            return None

def summarize_video(api_key, video_url, target_language, transcript):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    다음 YouTube 비디오 자막을 {target_language}로 요약해주세요:

    {transcript}

    이전 분석을 기반으로 하여 다음 구조로 분석을 이어가거나 완성해주세요:

    1. 주제 개요
    2. 핵심 내용 요약
    3. 상세 내용 분석
        [주요 섹션/주제]
        • 설명
        • 핵심 포인트
        • 세부 정보
        • 실용적 적용 또는 의의
    4. 사용된 방법론 또는 접근 방식
    5. 주요 인용구 또는 중요한 순간
    6. 시청자를 위한 가이드
    7. 추가 자료 및 리소스
    8. 비평적 분석 (해당되는 경우)
    9. 결론 및 향후 전망

    이 부분의 내용에 적합한 섹션만 분석하고, 나머지 섹션은 다음 부분에서 계속하겠다고 명시해주세요.
    """

    response = model.generate_content(prompt)
    return response.text

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{file_label}">다운로드 {file_label}</a>'
    return href

def main():
    st.title("YouTube 비디오 요약기")

    api_key = st.text_input("Gemini API 키를 입력하세요:", type="password", key="api_key_input")
    video_url = st.text_input("YouTube 비디오 URL을 입력하세요:", key="video_url_input")
    target_language = st.selectbox("요약 언어 선택:", ["ko", "en"], format_func=lambda x: "한국어" if x == "ko" else "English", key="language_select")

    if video_url:
        video_info = get_video_info(video_url)
        if video_info:
            st.subheader("영상 정보")
            st.write(f"제목: {video_info['title']}")
            st.write(f"설명: {video_info['description']}")
            st.write(f"조회수: {video_info['views']} 회")
            st.write(f"영상 길이: {video_info['length']} 초")
            st.write(f"게시 날짜: {video_info['publish_date']}")
            st.write(f"채널명: {video_info['channel_name']}")
            st.write(f"좋아요 수: {video_info['likes']} 개")
            st.write(f"싫어요 수: {video_info['dislikes']} 개")

            if st.button("영상 분석하기", key="analyze_button"):
                if api_key:
                    with st.spinner("비디오 분석 중..."):
                        video_id = get_video_id(video_url)
                        transcript = get_transcript(video_id, target_language)
                        if transcript:
                            summary = summarize_video(api_key, video_url, target_language, transcript)
                            st.subheader("요약")
                            st.markdown(summary)

                            # 스크립트 추출 및 다운로드 버튼
                            with open("transcript.txt", "w", encoding="utf-8") as f:
                                f.write(transcript)
                            st.markdown(get_binary_file_downloader_html("transcript.txt", "자막 스크립트"), unsafe_allow_html=True)

                            # 번역 버튼
                            if st.button("번역하기", key="translate_button"):
                                other_language = "en" if target_language == "ko" else "ko"
                                translator = GoogleTranslator(source=target_language, target=other_language)
                                translated_transcript = translator.translate(transcript)
                                st.write("번역된 자막:")
                                st.write(translated_transcript)
                        else:
                            st.error("자막을 가져오는데 실패했습니다.")
                else:
                    st.warning("API 키를 입력해주세요.")
        else:
            st.error("유효하지 않은 YouTube URL입니다.")

    st.markdown("---")
    st.markdown("이 앱은 Gemini API를 사용하여 YouTube 비디오를 요약합니다.")

if __name__ == "__main__":
    main()