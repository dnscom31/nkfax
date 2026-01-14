import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
from pypdf import PdfWriter, PdfReader  # PDF 병합을 위한 라이브러리
import base64
import os

# --- 파일 경로 설정 ---
FONT_PATH = "NanumGothic.ttf"
TEMPLATE_PATH = "background.png"

# 고정 첨부 파일
FILE_LICENSE = "개설허가증.pdf"
FILE_SPECIAL_CERT = "특수의료기관지정서.jpg"

# 의사별 면허증 매칭
DOCTOR_MAP = {
    "유민상": "유민상.pdf",
    "최윤범": "최윤범.pdf",
    "안형숙": "안형숙.pdf"
}

# --- 주소록 데이터 ---
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
    if not text: return
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    draw.text(position, str(text), fill=color, font=font)

def create_cover_pdf(data):
    """신고서 표지(1페이지) 생성"""
    try:
        image = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        # 좌표 매핑 (배경 이미지에 맞춰 조정 필요)
        add_text_to_image(draw, data['reg_date'], (150, 100))
        target_date_str = data['checkup_date'].strftime("%Y년 %m월 %d일")
        add_text_to_image(draw, target_date_str, (150, 420))
        time_str = f"{data['start_time'].strftime('%H:%M')} ~ {data['end_time'].strftime('%H:%M')}"
        add_text_to_image(draw, time_str, (150, 450))
        add_text_to_image(draw, data['location'], (150, 480))
        add_text_to_image(draw, data['target'], (150, 510))
        add_text_to_image(draw, f"{data['count']}명", (400, 540))
        add_text_to_image(draw, data['doctor_name'], (450, 650))
        
        today = datetime.now()
        add_text_to_image(draw, str(today.year), (180, 850))
        add_text_to_image(draw, str(today.month), (240, 850))
        add_text_to_image(draw, str(today.day), (300, 850))

        pdf_buffer = BytesIO()
        image.save(pdf_buffer, format="PDF", resolution=100.0)
        return pdf_buffer.getvalue()
    except Exception as e:
        st.error(f"표지 생성 오류: {e}")
        return None

def merge_documents(cover_pdf_bytes, doctor_name):
    """표지 + 의사면허증 + 개설허가증 + 특수지정서 병합"""
    merger = PdfWriter()
    
    try:
        # 1. 신고서 표지 추가
        merger.append(PdfReader(BytesIO(cover_pdf_bytes)))
        
        # 2. 의사 면허증 추가
        doc_file = DOCTOR_MAP.get(doctor_name)
        if doc_file and os.path.exists(doc_file):
            merger.append(PdfReader(doc_file))
        else:
            st.warning(f"⚠️ {doctor_name} 의사의 면허증 파일({doc_file})을 찾을 수 없습니다.")

        # 3. 개설허가증 추가
        if os.path.exists(FILE_LICENSE):
            merger.append(PdfReader(FILE_LICENSE))
        else:
            st.warning(f"⚠️ {FILE_LICENSE} 파일이 없습니다.")

        # 4. 특수의료기관지정서 (JPG -> PDF 변환 후 추가)
        if os.path.exists(FILE_SPECIAL_CERT):
            img_pdf_buffer = BytesIO()
            Image.open(FILE_SPECIAL_CERT).convert('RGB').save(img_pdf_buffer, format="PDF")
            merger.append(PdfReader(img_pdf_buffer))
        else:
            st.warning(f"⚠️ {FILE_SPECIAL_CERT} 파일이 없습니다.")

        # 병합된 결과 반환
        output_buffer = BytesIO()
        merger.write(output_buffer)
        return output_buffer.getvalue()

    except Exception as e:
        st.error(f"문서 병합 중 오류 발생: {e}")
        return None

def send_fax_barobill(pdf_bytes, receiver_num, sender_num):
    # 실제 바로빌 연동 시 st.secrets 사용 필요
    # payload = { ... "FileBase64": base64.b64encode(pdf_bytes).decode('utf-8') ... }
    return True, "전송 성공 (테스트 모드 - 4개 문서 병합됨)"

# --- UI 시작 ---
st.set_page_config(page_title="출장검진 팩스 발송", layout="wide")
st.title("🏥 출장 건강검진 신고서 통합 발송")

with st.form("fax_form"):
    st.subheader("1. 신고서 작성 및 의사 선택")
    
    col1, col2 = st.columns(2)
    with col1:
        reg_date = st.date_input("접수일", datetime.now())
        checkup_date = st.date_input("검진 일시", datetime.now())
        start_time = st.time_input("시작 시간", datetime.strptime("07:30", "%H:%M"))
        end_time = st.time_input("종료 시간", datetime.strptime("12:00", "%H:%M"))
    
    with col2:
        location = st.text_input("검진 장소", "김포시 통진읍 대서명로 49")
        target = st.text_input("검진 대상", "업체명 입력")
        count = st.number_input("예상 인원", value=50)
        
        # 의사 선택 (라디오 버튼 또는 셀렉트박스)
        doctor_name = st.selectbox("담당 의사 선택", ["유민상", "최윤범", "안형숙"])
        st.caption(f"📌 선택 시 '{DOCTOR_MAP[doctor_name]}' 파일이 자동으로 첨부됩니다.")

    st.markdown("---")
    st.subheader("2. 발송 정보")

    c1, c2 = st.columns([1, 1])
    with c1:
        selected_org = st.selectbox("수신처(보건소)", list(FAX_BOOK.keys()))
    with c2:
        receiver_fax = st.text_input("수신 팩스번호", value=FAX_BOOK[selected_org])

    sender_fax = st.text_input("발신 팩스번호", "031-987-7777")
    
    st.info("💡 '문서 생성' 버튼을 누르면 [신고서 + 의사면허증 + 개설허가증 + 특수지정서]가 하나의 PDF로 합쳐집니다.")
    submitted = st.form_submit_button("📄 통합 문서 생성 및 팩스 전송", use_container_width=True)

if submitted:
    if not receiver_fax:
        st.warning("⚠️ 수신번호를 입력하세요.")
    else:
        # 1. 표지 데이터 생성
        data = {
            'reg_date': reg_date, 'checkup_date': checkup_date,
            'start_time': start_time, 'end_time': end_time,
            'location': location, 'target': target,
            'count': count, 'doctor_name': doctor_name
        }
        
        # 2. 표지 PDF 생성
        cover_bytes = create_cover_pdf(data)
        
        if cover_bytes:
            # 3. 전체 문서 병합 (표지 + 의사 + 허가증 + 지정서)
            merged_pdf_bytes = merge_documents(cover_bytes, doctor_name)
            
            if merged_pdf_bytes:
                r1, r2 = st.columns(2)
                with r1:
                    st.success(f"✅ 총 4개의 문서가 병합되었습니다.")
                    st.download_button("📥 통합 PDF 다운로드", merged_pdf_bytes, "통합신고서.pdf")
                with r2:
                    with st.spinner("🖨️ 팩스 전송 중..."):
                        success, msg = send_fax_barobill(merged_pdf_bytes, receiver_fax, sender_fax)
                        if success: st.info(f"결과: {msg}")
                        else: st.error(f"실패: {msg}")
