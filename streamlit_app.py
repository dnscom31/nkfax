import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
import base64

# --- 설정 및 상수 ---
FONT_PATH = "NanumGothic.ttf"  # 폰트 파일 경로
TEMPLATE_PATH = "background.png"  # 배경 이미지 파일 경로

# --- 주소록 데이터 (제공해주신 데이터 반영) ---
FAX_BOOK = {
    "직접 입력": "",
    "김포시 보건소": "031-5186-4129",
    "인천 강화군": "032-930-3642",
    "인천 서구": "032-718-0790",
    "인천시 중구": "032-760-6018",
    "인천시 동구": "032-770-5709",
    "인천시 미추홀구": "032-770-5790",
    "인천시 옹진군": "032-899-3129",
    "인천시 부평구": "032-509-8290",
    "인천시 남동구": "032-453-5079",
    "인천시 계양구": "032-551-5772",
    "인천 연수구": "032-749-8049",
    "파주시": "031-940-4889",
    "파주 운정": "031-820-7309",
    "부천시": "0502-4002-4214",
    "부천시 오정구": "032-625-4359",
    "안양 동안구": "031-8045-6577",
    "서울 강서구": "02-2620-0507",
    "서울 영등포": "02-2670-4877",
    "서울 구로": "02-860-2653",
    "서울 종로": "02-2148-5840",
    "서울 서대문": "02-330-1854",
    "서울 동대문": "02-3299-2643",
    "서울 마포구": "02-3153-9159",
    "서울 중구": "02-3396-8910",
    "서울 양천구": "02-6948-5571",
    "서울 강남": "02-3423-8903",
    "서울 용산구": "02-2199-5830",
    "서울 성동구": "02-2286-7062",
    "고양 일산서구": "031-976-2040",
    "고양 일산동구": "031-8075-4885",
    "고양시 덕양구": "031-968-0217",
    "군포시": "031-461-5466",
    "양주시": "0505-041-1924"
}

def add_text_to_image(draw, text, position, font_size=15, color="black"):
    """이미지의 특정 좌표에 텍스트를 그리는 함수"""
    if not text:
        return
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    
    draw.text(position, str(text), fill=color, font=font)

def create_fax_document(data):
    """입력받은 데이터를 배경 이미지에 합성하여 PDF 바이너리로 반환"""
    try:
        image = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        # --- 좌표 매핑 (background.png에 맞춰 미세 조정 필요) ---
        add_text_to_image(draw, data['reg_date'], (150, 100)) # 접수일
        
        target_date_str = data['checkup_date'].strftime("%Y년 %m월 %d일")
        add_text_to_image(draw, target_date_str, (150, 420)) # 일시
        
        time_str = f"{data['start_time'].strftime('%H:%M')} ~ {data['end_time'].strftime('%H:%M')}"
        add_text_to_image(draw, time_str, (150, 450)) # 시간
        
        add_text_to_image(draw, data['location'], (150, 480)) # 장소
        add_text_to_image(draw, data['target'], (150, 510)) # 대상
        add_text_to_image(draw, f"{data['count']}명", (400, 540)) # 인원수
        add_text_to_image(draw, data['doctor_name'], (450, 650)) # 의사명
        
        # 하단 신고일 (현재 날짜)
        today = datetime.now()
        add_text_to_image(draw, str(today.year), (180, 850))
        add_text_to_image(draw, str(today.month), (240, 850))
        add_text_to_image(draw, str(today.day), (300, 850))

        pdf_buffer = BytesIO()
        image.save(pdf_buffer, format="PDF", resolution=100.0)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"문서 생성 중 오류 발생: {e}")
        return None

def send_fax_barobill(pdf_bytes, receiver_num, sender_num):
    """바로빌 API를 이용해 팩스 전송 (구조 예시)"""
    file_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # 실제 전송 로직 (secrets 사용)
    # payload = {
    #     "CERTKEY": st.secrets["BAROBILL_CERT_KEY"],
    #     "CorpNum": st.secrets["BAROBILL_CORP_NUM"],
    #     "SenderNum": sender_num,
    #     "ReceiverNum": receiver_num,
    #     "FileBase64": file_base64,
    #     "Subject": "출장건강검진신고서"
    # }
    # requests.post(...) 
    
    return True, "전송 성공 (테스트 모드)"

# --- Streamlit UI 시작 ---
st.set_page_config(page_title="출장검진 신고서 팩스", layout="wide")

st.title("🏥 출장 건강검진 신고서 자동 팩스")

with st.form("fax_form"):
    st.subheader("1. 신고서 내용 작성")
    
    col1, col2 = st.columns(2)
    with col1:
        reg_date = st.date_input("접수일", datetime.now())
        checkup_date = st.date_input("검진 일시", datetime.now())
        start_time = st.time_input("시작 시간", datetime.strptime("07:30", "%H:%M"))
        end_time = st.time_input("종료 시간", datetime.strptime("12:00", "%H:%M"))
    
    with col2:
        location = st.text_input("검진 장소", "김포시 통진읍 대서명로 49 (1층 직원식당)")
        target = st.text_input("검진 대상", "업체명 입력")
        count = st.number_input("예상 인원 수", value=50)
        doctor_name = st.text_input("의사 성명", "유민상")

    st.markdown("---")
    st.subheader("2. 팩스 발송 정보")

    # --- 발송처 선택 로직 ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        # 보건소 선택 드롭다운
        selected_org = st.selectbox(
            "수신처(보건소) 선택", 
            list(FAX_BOOK.keys()), 
            index=0
        )
    
    with c2:
        # 선택된 보건소의 번호를 가져옴
        prefilled_fax = FAX_BOOK[selected_org]
        
        # 텍스트 입력창에 미리 채워넣음 (수정 가능)
        receiver_fax = st.text_input(
            "수신 팩스번호 (직접 수정 가능)", 
            value=prefilled_fax,
            help="목록에서 선택하면 자동 입력되며, 필요 시 직접 숫자를 지우고 다시 입력할 수 있습니다."
        )

    sender_fax = st.text_input("발신 팩스번호", "031-987-7777")

    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("📄 문서 생성 및 팩스 전송", use_container_width=True)

# --- 폼 제출 후 처리 ---
if submitted:
    if not receiver_fax:
        st.warning("수신 팩스번호를 입력해주세요.")
    else:
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
            # 2. 결과 화면 분할
            res_col1, res_col2 = st.columns([1, 1])
            
            with res_col1:
                st.success("✅ 문서 이미지가 생성되었습니다.")
                st.download_button("📥 생성된 PDF 다운로드", pdf_bytes, "report.pdf")
            
            with res_col2:
                # 3. 팩스 전송 시도
                with st.spinner(f"🖨️ {receiver_fax}로 팩스 전송 중..."):
                    success, msg = send_fax_barobill(pdf_bytes, receiver_fax, sender_fax)
                    if success:
                        st.info(f"결과: {msg}")
                    else:
                        st.error(f"실패: {msg}")
