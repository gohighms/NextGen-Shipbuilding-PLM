# apps/main_app.py
import streamlit as st
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from modules.cad_engine.parser import extract_bom_from_step
from modules.digital_thread.data_manager import get_digital_thread_data

# 페이지 대시보드 설정
st.set_page_config(page_title="NexGen Ship PLM", layout="wide")

st.title("🚢 Next-Gen Shipbuilding PLM Platform")

# 사이드바 메뉴
st.sidebar.header("Control Panel")
menu = st.sidebar.radio("Navigation", ["Visual BOM Engine", "Digital Thread", "Knowledge Graph"])

if menu == "Visual BOM Engine":
    st.subheader("BOM Extraction from CAD Data")
    
    # 파일 업로드
    uploaded_file = st.file_uploader("Upload STEP File (.stp / .step)", type=["stp", "step"])
    
    # 파서 호출하여 데이터 가져오기
    bom_list = extract_bom_from_step(uploaded_file)
    
    # 화면 분할 (BOM 리스트 / 3D 뷰어 예비)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("### 📂 Engineering BOM")
        # 표 형식으로 출력
        st.table(bom_list)
        
    with col2:
        st.write("### 🎨 Visual Preview")
        st.info("3D 렌더링 모듈 준비 중입니다.")
        
elif menu == "2. Digital Thread Mapper":
    st.header("🔗 Digital Thread Mapper")
    st.markdown("##### 통합 데이터 흐름: Spec ➔ Purchase ➔ Design ➔ Production")
    
    # 데이터 로드
    thread_data = get_digital_thread_data()
    
    # 1. 시각적인 Flow 차트 (Streamlit의 간단한 단계 표시 활용)
    st.write("### 🏗️ Thread Continuity Status")
    for item in thread_data:
        with st.expander(f"TAG: {item['TAG']} - Lifecycle Trace"):
            cols = st.columns(4)
            cols[0].metric("1. Spec", "Verified")
            cols[1].metric("2. Purchase", "Ordered")
            cols[2].metric("3. Design", "Released")
            cols[3].metric("4. Production", "In-Progress")
            
            st.json(item) # 실제 데이터 상세 확인

    # 2. 통합 관리 테이블
    st.write("### 📊 Master Thread Table")
    st.dataframe(thread_data, use_container_width=True)

