import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import json
import base64
from io import BytesIO
from datetime import datetime

# --- 설정 및 상수 ---
# 한글 폰트 경로 (같은 폴더에 NanumGothic.ttf 파일을 넣어주세요)
FONT_PATH = "NanumGothic.ttf" 
# 배경 이미지 경로 (HWP를 이미지로 변환한 파일)
TEMPLATE_PATH = "background.png"

# --- 바로빌 API 설정 (실제 키는 Streamlit Secrets에서 관리 권장) ---
BAROBILL_API_URL = "https://ws.barobill.co.kr/Fax/FaxService.asmx/SendFax" # 예시 URL (문서 확인 필요)
# 실제 바로빌 REST API 엔드포인트는 개발 가이드 문서를 확인하여 정확한 URL을 입력해야 합니다.
# 일반적으로 SOAP을 많이 쓰지만, JSON 지원 여부를 확인해야 합니다. 
# 여기서는 일반적인 POST 요청 구조로 작성합니다.

def add_text_to_image(draw, text, position, font_size=15, color="black"):
    """이미지의 특정 좌표에 텍스트를 그리는 함수"""
    if not text:
        return
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default() # 폰트 파일 없으면 기본 폰트
    
    draw.text(position, str(text), fill=color, font=font)

def create_fax_document(data):
    """입력받은 데이터를 배경 이미지에 합성하여 PDF 바이너리로 반환"""
    try:
        image = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        # --- 좌표 매핑 (실제 이미지 크기에 맞춰 x, y 수정 필요) ---
        # 예시 좌표입니다. 실제 background.png 해상도에 맞춰 조정하세요.
        
        # 1. 접수일 (상단)
        add_text_to_image(draw, data['reg_date'], (150, 100)) # (x, y)
        
        # 2. 일시 (년 월 일)
        target_date_str = data['checkup_date'].strftime("%Y년 %m월 %d일")
        add_text_to_image(draw, target_date_str, (150, 420))
        
        # 3. 시간
        time_str = f"{data['start_time'].strftime('%H:%M')} ~ {data['end_time'].strftime('%H:%M')}"
        add_text_to_image(draw, time_str, (150, 450))
        
        # 4. 장소
        add_text_to_image(draw, data['location'], (150, 480))
        
        # 5. 대상
        add_text_to_image(draw, data['target'], (150, 510))
        
        # 6. 예상인원 수
        add_text_to_image(draw, f"{data['count']}명", (400, 540))
        
        # 7. 수행인원(의사)
        add_text_to_image(draw, data['doctor_name'], (450, 650))
        
        # 8. 하단 신고일 (년 월 일)
        today = datetime.now()
        add_text_to_image(draw, str(today.year), (180, 850))
        add_text_to_image(draw, str(today.month), (240, 850))
        add_text_to_image(draw, str(today.day), (300, 850))

        # PDF로 변환
        pdf_buffer = BytesIO()
        image.save(pdf_buffer, format="PDF", resolution=100.0)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"문서 생성 중 오류 발생: {e}")
        return None

def send_fax_barobill(pdf_bytes, receiver_num, sender_num):
    """바로빌 API를 이용해 팩스 전송"""
    
    # API 호출을 위한 인코딩 (Base64)
    file_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # 바로빌 API 명세에 따른 Payload 구성 (예시)
    # 주의: 실제 바로빌 키(CertKey, CorpNum 등)는 st.secrets에서 가져와야 함
    payload = {
        "CERTKEY": st.secrets["BAROBILL_CERT_KEY"],
        "CorpNum": st.secrets["BAROBILL_CORP_NUM"],
        "SenderNum": sender_num,
        "ReceiverNum": receiver_num,
        "FileBase64": file_base64, # 또는 파일 업로드 방식에 따라 변경
        "Subject": "출장건강검진신고서"
    }
    
    # 실제 구현 시 바로빌의 Python SDK를 쓰거나 REST API 명세에 맞춰 requests.post 사용
    # 여기서는 구조만 잡습니다.
    # response = requests.post(BAROBILL_API_URL, json=payload)
    
    # 테스트를 위한 가짜 응답
    return True, "전송 성공 (테스트 모드)"

# --- Streamlit UI ---
st.title("🏥 건강검진 신고서 팩스 자동 발송")

with st.form("fax_form"):
    st.subheader("1. 신고 내용 입력")
    
    col1, col2 = st.columns(2)
    with col1:
        reg_date = st.date_input("접수일", datetime(2023, 10, 10))
        checkup_date = st.date_input("검진 일시", datetime(2023, 10, 20))
        start_time = st.time_input("시작 시간", datetime.strptime("07:30", "%H:%M"))
        end_time = st.time_input("종료 시간", datetime.strptime("12:00", "%H:%M"))
    
    with col2:
        location = st.text_input("장소", "김포시 통진읍 대서명로 49 (1층 직원식당)")
        target = st.text_input("대상", "사이몬")
        count = st.number_input("예상 인원 수", value=50)
        doctor_name = st.text_input("의사 성명", "유민상")

    st.subheader("2. 발송 정보")
    sender_fax = st.text_input("발신 팩스번호", "031-987-7777")
    
    # 주소록 관리 (딕셔너리로 관리하거나 DB 연동 가능)
    address_book = {
        "김포시 보건소": "031-000-0000", # 실제 번호로 수정 필요
        "테스트용": "000-0000-0000"
    }
    receiver_name = st.selectbox("수신처 선택", list(address_book.keys()))
    receiver_fax = st.text_input("수신 팩스번호", address_book[receiver_name])

    submitted = st.form_submit_button("문서 생성 및 팩스 전송")

if submitted:
    data = {
        'reg_date': reg_date,
        'checkup_date': checkup_date,
        'start_time': start_time,
        'end_time': end_time,
        'location': location,
        'target': target,
        'count': count,
        'doctor_name': doctor_name
    }
    
    # 1. 문서 생성
    pdf_bytes = create_fax_document(data)
    
    if pdf_bytes:
        st.success("문서 이미지가 생성되었습니다.")
        # 미리보기 제공 (선택사항)
        st.download_button("생성된 PDF 다운로드", pdf_bytes, "report.pdf")
        
        # 2. 팩스 전송
        with st.spinner("팩스 전송 중..."):
            success, msg = send_fax_barobill(pdf_bytes, receiver_fax, sender_fax)
            if success:
                st.success(f"✅ 전송 완료: {msg}")
            else:
                st.error(f"❌ 전송 실패: {msg}")
