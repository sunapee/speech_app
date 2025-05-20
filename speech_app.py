import streamlit as st
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import os
import numpy as np
import time
import wave
import io
from datetime import datetime

# ページの設定
st.set_page_config(
    page_title="音声文字変換ツール",
    page_icon="🎤",
    layout="wide"
)

# CSSスタイルを追加
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #E8F5E9;
        border-radius: 0.5rem;
        border-left: 0.5rem solid #4CAF50;
    }
    .info-box {
        padding: 1rem;
        background-color: #E3F2FD;
        border-radius: 0.5rem;
        border-left: 0.5rem solid #2196F3;
        margin-bottom: 1rem;
    }
    .timestamp {
        color: #616161;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# アプリのタイトル
st.markdown("<h1 class='main-header'>音声文字変換ツール</h1>", unsafe_allow_html=True)

# アプリの説明
st.markdown("<div class='info-box'>このアプリは、音声ファイルをテキストに変換したり、マイクからリアルタイムで音声を文字起こしするツールです。会議の記録や議事録作成に役立ちます。</div>", unsafe_allow_html=True)

# サイドバーでモード選択
mode = st.sidebar.radio(
    "モードを選択してください",
    ["ファイルから変換", "マイクからリアルタイム文字起こし"]
)

# 言語選択
language_options = {
    "日本語": "ja-JP",
    "英語": "en-US",
    "中国語": "zh-CN",
    "韓国語": "ko-KR",
    "フランス語": "fr-FR",
    "ドイツ語": "de-DE",
    "スペイン語": "es-ES"
}
selected_language = st.sidebar.selectbox(
    "言語を選択してください",
    list(language_options.keys())
)
language_code = language_options[selected_language]

# 音声をテキストに変換する関数
def transcribe_audio(audio_data, language="ja-JP"):
    r = sr.Recognizer()
    try:
        text = r.recognize_google(audio_data, language=language)
        return text
    except sr.UnknownValueError:
        return "音声を認識できませんでした"
    except sr.RequestError as e:
        return f"Google Speech Recognition サービスに接続できませんでした; {e}"

# 音声ファイルを分割して変換する関数
def process_audio_file(file_path, language="ja-JP", chunk_size=60000):  # チャンクサイズは60秒（60000ミリ秒）
    try:
        # 音声ファイルの読み込み
        audio = AudioSegment.from_file(file_path)
        
        # 結果格納用のリスト
        transcription_results = []
        
        # 進捗バーの表示
        chunks = list(range(0, len(audio), chunk_size))
        progress_bar = st.progress(0)
        
        for i, start in enumerate(chunks):
            # チャンクの終了位置を計算
            end = min(start + chunk_size, len(audio))
            
            # 音声のチャンク部分を切り出し
            chunk = audio[start:end]
            
            # 一時ファイルとして保存
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as temp_file:
                chunk.export(temp_file.name, format="wav")
                
                # 音声認識オブジェクトの作成
                r = sr.Recognizer()
                with sr.AudioFile(temp_file.name) as source:
                    audio_data = r.record(source)
                    
                    # 音声認識
                    try:
                        text = r.recognize_google(audio_data, language=language)
                        time_str = format_time(start)
                        transcription_results.append({"time": time_str, "text": text})
                    except sr.UnknownValueError:
                        time_str = format_time(start)
                        transcription_results.append({"time": time_str, "text": "(認識できませんでした)"})
                    except sr.RequestError as e:
                        st.error(f"Google Speech Recognition サービスに接続できませんでした: {e}")
                        return []
            
            # 進捗バーの更新
            progress_bar.progress((i + 1) / len(chunks))
        
        return transcription_results
    except Exception as e:
        st.error(f"音声処理中にエラーが発生しました: {e}")
        return []

# ミリ秒を時間形式に変換する関数
def format_time(ms):
    seconds = int(ms / 1000)
    minutes = int(seconds / 60)
    seconds %= 60
    return f"{minutes:02d}:{seconds:02d}"

# 文字起こし結果を表示する関数
def display_transcription(results):
    if not results:
        st.warning("文字起こし結果がありません")
        return
    
    st.markdown("<h3 class='sub-header'>文字起こし結果</h3>", unsafe_allow_html=True)
    
    # 結果を表示
    for result in results:
        st.markdown(f"<span class='timestamp'>{result['time']}</span> {result['text']}", unsafe_allow_html=True)
    
    # 文字起こし結果をテキストファイルとしてダウンロードできるように
    result_text = "\n".join([f"{r['time']} {r['text']}" for r in results])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcription_{timestamp}.txt"
    
    st.download_button(
        label="文字起こし結果をダウンロード",
        data=result_text,
        file_name=filename,
        mime="text/plain"
    )

# ファイルからの変換モード
if mode == "ファイルから変換":
    st.markdown("<h2 class='sub-header'>音声ファイルから文字起こし</h2>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("音声ファイルをアップロードしてください", type=['mp3', 'wav', 'ogg', 'flac', 'm4a'])
    
    if uploaded_file is not None:
        # 音声ファイルの情報表示
        file_details = {"ファイル名": uploaded_file.name, "ファイルサイズ": f"{uploaded_file.size / 1024 / 1024:.2f} MB"}
        st.write(file_details)
        
        # 音声の再生
        st.audio(uploaded_file, format=f'audio/{uploaded_file.name.split(".")[-1]}')
        
        # 一時ファイルとして保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        # 文字起こしの実行
        if st.button("文字起こしを開始"):
            with st.spinner("音声を処理しています..."):
                results = process_audio_file(tmp_file_path, language=language_code)
                display_transcription(results)
            
            # 一時ファイルの削除
            os.unlink(tmp_file_path)

# マイクからリアルタイム文字起こしモード
else:
    st.markdown("<h2 class='sub-header'>マイクからリアルタイム文字起こし</h2>", unsafe_allow_html=True)
    st.markdown("<div class='info-box'>「録音開始」ボタンを押すと、マイクからの音声をリアルタイムで文字起こしします。<br>会議中の発言などを記録するのに役立ちます。</div>", unsafe_allow_html=True)
    
    # セッション状態の初期化
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'transcription' not in st.session_state:
        st.session_state.transcription = []
    
    # 録音の開始/停止を制御するボタン
    col1, col2 = st.columns(2)
    
    if not st.session_state.recording:
        if col1.button("録音開始"):
            st.session_state.recording = True
            st.rerun()
    else:
        if col2.button("録音停止"):
            st.session_state.recording = False
            st.rerun()
    
    # 録音中の場合
    if st.session_state.recording:
        st.markdown("<div class='success-box'>録音中... 話してください</div>", unsafe_allow_html=True)
        
        # マイクから音声を取得
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.write("音声を聞いています...")
            
            # 環境ノイズに合わせた調整
            r.adjust_for_ambient_noise(source)
            
            try:
                audio_data = r.listen(source, timeout=5, phrase_time_limit=10)
                st.write("音声を処理しています...")
                
                # 音声認識
                try:
                    text = transcribe_audio(audio_data, language=language_code)
                    if text and text != "音声を認識できませんでした":
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.transcription.append({"time": timestamp, "text": text})
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
            
            except sr.WaitTimeoutError:
                st.warning("音声が検出されませんでした。もう一度お試しください。")
    
    # 文字起こし結果の表示
    if st.session_state.transcription:
        st.markdown("<h3 class='sub-header'>文字起こし結果</h3>", unsafe_allow_html=True)
        
        for item in st.session_state.transcription:
            st.markdown(f"<span class='timestamp'>{item['time']}</span> {item['text']}", unsafe_allow_html=True)
        
        # 結果のクリアボタン
        if st.button("文字起こし結果をクリア"):
            st.session_state.transcription = []
            st.rerun()
        
        # 文字起こし結果をテキストファイルとしてダウンロードできるように
        result_text = "\n".join([f"{r['time']} {r['text']}" for r in st.session_state.transcription])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"realtime_transcription_{timestamp}.txt"
        
        st.download_button(
            label="文字起こし結果をダウンロード",
            data=result_text,
            file_name=filename,
            mime="text/plain"
        )

# フッター
st.markdown("---")
st.markdown("音声文字変換ツール © 2025")