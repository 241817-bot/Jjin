
import streamlit as st
import pandas as pd
import json
import os
import re
import zipfile

st.set_page_config(page_title='국어 규범 통합 진단 도우미', layout='wide', page_icon='📖')

# --- 신규: 데이터 자동 병합 및 압축 해제 로직 ---
def prepare_data():
    data_dir = './rlhf_data/'
    # 폴더가 없으면 생성하고 ZIP 해제 시도
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    zip_parts = ['rlhf_data_part1.zip', 'rlhf_data_part2.zip']
    for zip_file in zip_parts:
        if os.path.exists(zip_file):
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(data_dir)

# 앱 시작 시 데이터 준비 실행
prepare_data()

# 1. 통합 규정 및 발음 데이터베이스
grammar_db = {
    '제47항': {
        'name': '제47항 보조 용언',
        'rule': '보조 용언은 띄어 씀을 원칙으로 하되, 붙여 씀도 허용함.',
        'daman': '다만, 앞말에 조사가 붙거나 합성 동사인 경우 등은 무조건 띄어 써야 함.',
        'reasoning': '본용언이 합성 동사거나 조사가 결합된 경우 가독성을 위해 띄어쓰기를 강제합니다.',
        'patterns': ['버렸다', '본다', '난다', '간다'],
        'pronunciation_step': [
            "1단계: 기본 발음 확인 ([버렸다])",
            "2단계: 'ㅆ' 받침이 'ㄷ'으로 대표음화 ([버렫다])",
            "3단계: 뒤 음절 '다'의 된소리 현상 ([버렫따])",
            "최종 발음: [버렫따]"
        ]
    },
    '제48항': {
        'name': '제48항 성명과 호칭',
        'rule': '성과 이름은 붙여 쓰고, 호칭어는 띄어 씀.',
        'daman': '다만, 성과 이름이 혼동될 우려가 있는 경우는 띄어 쓸 수 있음.',
        'reasoning': '독고준, 남궁억처럼 성과 이름의 경계가 모호할 때 사용자의 편의를 위한 예외 조항입니다.',
        'patterns': ['남궁', '독고', '황보'],
        'pronunciation_step': [
            "1단계: 성과 이름 경계 확인 ([남궁] + [억])",
            "2단계: 연음 법칙 적용 (앞 받침 'ㅇ'이 뒤로 이어짐)",
            "최종 발음: [남궁억]"
        ]
    },
    '제49항': {
        'name': '제49항 고유 명사',
        'rule': '성명 이외의 고유 명사는 단어별로 띄어 씀을 원칙으로 함.',
        'daman': '다만, 단위별로 붙여 쓸 수 있음.',
        'reasoning': '긴 고유 명사의 경우 가독성과 의미 전달을 위해 붙여쓰기를 허용합니다.',
        'patterns': ['대학교', '초등학교', '병원', '연구소'],
        'pronunciation_step': [
            "1단계: 각 단어 독립 발음 확인",
            "2단계: 합성어 내 사이시옷 또는 연음 확인",
            "최종 발음: [문맥에 따른 표준 발음 적용]"
        ]
    },
    '문장부호': {
        'name': '문장 부호 (마침표)',
        'rule': '문장의 끝에 마침표를 찍는 것이 원칙임.',
        'daman': '다만, 제목이나 표어에는 마침표를 쓰지 않음.',
        'reasoning': '간결함이 생명인 제목이나 표어에서는 시각적 간결성을 위해 생략을 원칙으로 합니다.',
        'patterns': ['.', '!', '?'],
        'pronunciation_step': ["해당 사항 없음"]
    }
}

@st.cache_data
def get_corpus_examples(keyword):
    data_dir = './rlhf_data/'
    results = []
    if not os.path.exists(data_dir): return ["(데이터 로딩 중...)"]

    # 하위 폴더까지 검색하도록 수정
    json_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))

    for f_path in json_files[:10]: # 성능을 위해 10개 파일만 우선 검색
        with open(f_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data.get('utterance', []):
                form = item.get('form', '')
                if keyword in form:
                    results.append(form)
                    if len(results) >= 5: break
        if len(results) >= 5: break
    return results

st.title('🔍 국어 규범 통합 진단 & 발음 서비스')
st.markdown('### 표준국어대사전 기반 교정, 발음 단계 및 말뭉치 사례 분석')

user_sentence = st.text_input('진단할 문장을 입력하세요:', placeholder='예: 떠내려가버렸다, 남궁억, 한국대학교')

if user_sentence:
    st.divider()
    col1, col2 = st.columns(2)
    target_rule = None
    suggestion = user_sentence

    if any(p in user_sentence for p in ['버렸다', '본다']):
        target_rule = grammar_db['제47항']
        if '떠내려가버렸다' in user_sentence.replace(' ', ''): suggestion = user_sentence.replace('떠내려가버렸다', '떠내려가 버렸다')
    elif any(p in user_sentence for p in grammar_db['제48항']['patterns']):
        target_rule = grammar_db['제48항']
    elif any(p in user_sentence for p in grammar_db['제49항']['patterns']):
        target_rule = grammar_db['제49항']
        if ' ' in user_sentence: suggestion = user_sentence.replace(' ', '')
    elif user_sentence.endswith('.'):
        target_rule = grammar_db['문장부호']

    with col1:
        st.subheader('📝 규정 진단 및 발음 안내')
        if target_rule:
            st.info(f"**진단된 규정:** {target_rule['name']}")
            st.success(f"✅ **권장 수정/허용:** {suggestion}")
            with st.expander('🗣️ 어떻게 발음하나요?'):
                for step in target_rule['pronunciation_step']: st.write(step)
            st.markdown(f"**[규정]** {target_rule['rule']}")
            st.warning(f"**[예외]** {target_rule['daman']}")
        else:
            st.write("입력한 문장에 해당하는 규정 데이터를 분석 중입니다.")

    with col2:
        st.subheader('📚 말뭉치 실제 사용 사례')
        search_key = user_sentence.split()[-1][:2] if ' ' in user_sentence else user_sentence[:2]
        examples = get_corpus_examples(search_key)
        if examples:
            for ex in examples: st.write(f"- {ex}")
        else: st.write("유사 사례 없음")
else:
    st.info('문장을 입력하여 진단을 시작하세요.')
