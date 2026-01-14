import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
from pypdf import PdfWriter, PdfReader
import base64
import os
from zeep import Client

# --- 설정 및 상수 ---
FONT_PATH = "NanumGothic.ttf"
TEMPLATE_PATH = "background.png"       # 기존 신고서 배경
TEMPLATE_FIX_PATH = "background_fix001.png" # 새로 추가된 변경/취소 배경

# 고정 첨부 파일
FILE_LICENSE = "개설허가증.pdf"
FILE_SPECIAL_CERT = "특수의료기관지정서.jpg"

# 의사별 면허증 매칭
DOCTOR_MAP = {
    "유민상": "유민상.pdf",
    "최윤범": "최윤범.pdf",
    "안형숙": "안형숙.pdf"
}

# --- 바로빌 API 설정 ---
BAROBILL_WSDL_URL = "https://ws.baroservice.com/FAX.asmx?WSDL"

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

def create_report_pdf(data):
    """[기존] 신고서 표지 생성"""
    try:
        image = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        # 좌표 매핑 (기존)
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
        st.error(f"신고서 표지 생성 오류: {e}")
        return None

def create_fix_pdf(data):
    """[신규] 변경/취소 신청서 생성"""
    try:
        image = Image.open(TEMPLATE_FIX_PATH).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        # 1. 상단 체크박스 (변경 vs 취소)
        # 좌표는 background_fix001.png의 실제 크기에 따라 조정 필요
        # 예시: 변경[550, 85], 취소[550, 130] -> 실제 이미지 확인 후 수정 요망
        if data['type'] == 'change':
            add_text_to_image(draw, "V", (550, 85), font_size=20, color="red") # 변경 체크
        else:
            add_text_to_image(draw, "V", (550, 130), font_size=20, color="red") # 취소 체크

        # 2. 접수일 (선택 사항, 필요하면 추가)
        # add_text_to_image(draw, data['reg_date'], (250, 170))

        # 3. 변경 사항 입력 (행별 좌표 설정)
        # 열 좌표 예시: 변경전 X=350, 변경후 X=900
        # 행 좌표 예시: 일시 Y=950, 장소 Y=1050 ... (간격 약 100px 가정)
        
        row_start_y = 950
        row_gap = 100
        col_before_x = 350
        col_after_x = 900

        # 데이터 매핑 (항목 순서대로)
        # items: [일시, 장소, 대상, 인원수, 인력, 항목, 기타]
        items = ['date', 'place', 'target', 'count', 'staff', 'items', 'etc']
        
        for i, item in enumerate(items):
            y_pos = row_start_y + (i * row_gap)
            before_val = data.get(f'{item}_before', '')
            after_val = data.get(f'{item}_after', '')
            
            add_text_to_image(draw, before_val, (col_before_x, y_pos))
            add_text_to_image(draw, after_val, (col_after_x, y_pos))

        # 4. 취소 사유 (취소일 경우 하단에 표시)
        if data['type'] == 'cancel':
            # 취소 사유 좌표 예시
            add_text_to_image(draw, data['cancel_reason'], (300, 1750))

        # 5. 하단 작성일 (오늘 날짜)
        today = datetime.now()
        # 좌표 예시: 년(1600, 2200) 월(1700, 2200) 일(1800, 2200)
        # 이미지 해상도에 따라 이 좌표는 반드시 튜닝해야 합니다.
        add_text_to_image(draw, str(today.year), (1200, 2200))
        add_text_to_image(draw, str(today.month), (1350, 2200))
        add_text_to_image(draw, str(today.day), (1450, 2200))

        pdf_buffer = BytesIO()
        image.save(pdf_buffer, format="PDF", resolution=100.0)
        return pdf_buffer.getvalue()

    except Exception as e:
        st.error(f"변경신청서 생성 오류: {e}")
        return None

def merge_documents(cover_pdf_bytes, doctor_name):
    """표지 + 의사면허증 + 개설허가증 + 특수지정서 병합"""
    merger = PdfWriter()
    try:
        merger.append(PdfReader(BytesIO(cover_pdf_bytes)))
        
        doc_file = DOCTOR_MAP.get(doctor_name)
        if doc_file and os.path.exists(doc_file):
            merger.append(PdfReader(doc_file))
        
        if os.path.exists(FILE_LICENSE):
            merger.append(PdfReader(FILE_LICENSE))

        if os.path.exists(FILE_SPECIAL_CERT):
            img_pdf_buffer = BytesIO()
            Image.open(FILE_SPECIAL_CERT).convert('RGB').save(img_pdf_buffer, format="PDF")
            merger.append(PdfReader(img_pdf_buffer))

        output_buffer = BytesIO()
        merger.write(output_buffer)
        return output_buffer.getvalue()
    except Exception as e:
        st.error(f"문서 병합 오류: {e}")
        return None

def send_fax_barobill_real(pdf_bytes, receiver_num, sender_num):
    """바로빌 API 팩스 전송"""
    try:
        if "BAROBILL_CERT_KEY" not in st.secrets:
            return False, "API 키(Secrets)가 설정되지 않았습니다."
            
        cert_key = st.secrets["BAROBILL_CERT_KEY"]
        corp_num = st.secrets["BAROBILL_CORP_NUM"]
        sender_id = st.secrets["BAROBILL_ID"]

        file_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        client = Client(BAROBILL_WSDL_URL)
        
        result = client.service.SendFax(
            CERTKEY=cert_key,
            CorpNum=corp_num,
            SenderID=sender_id,
            SenderNum=sender_num.replace("-", ""),
            ReceiverNum=receiver_num.replace("-", ""), 
            ReceiverName="보건소",
            FileBase64=file_base64,
            Subject="출장검진신고서",
            SendDT="",
            RefKey=""
        )
        
        if int(result) < 0:
            return False, f"전송 실패 (에러코드: {result})"
        else:
            return True, f"전송 접수 완료 (접수번호: {result})"
    except Exception as e:
        return False, f"API 통신 오류: {str(e)}"

# --- UI 메인 시작 ---
st.set_page_config(page_title="출장검진 팩스 시스템", layout="wide")
st.title("🏥 뉴고려병원 출장검진 팩스 시스템")

# 탭 생성
tab1, tab2 = st.tabs(["📑 출장검진 신고서", "📝 변경/취소 신청서"])

# ==========================================
# 탭 1: 기존 출장검진 신고서
# ==========================================
with tab1:
    with st.form("report_form"):
        st.subheader("1. 신고서 내용 작성")
        c1, c2 = st.columns(2)
        with c1:
            reg_date = st.date_input("접수일", datetime.now())
            checkup_date = st.date_input("검진 일시", datetime.now())
            start_time = st.time_input("시작 시간", datetime.strptime("07:30", "%H:%M"))
            end_time = st.time_input("종료 시간", datetime.strptime("12:00", "%H:%M"))
        with c2:
            location = st.text_input("장소", "김포시 통진읍 대서명로 49")
            target = st.text_input("대상", "업체명 입력")
            count = st.number_input("인원 수", value=50)
            doctor_name = st.selectbox("담당 의사", ["유민상", "최윤범", "안형숙"])

        st.markdown("---")
        st.subheader("2. 발송 정보")
        rc1, rc2 = st.columns(2)
        with rc1:
            selected_org = st.selectbox("수신처(보건소)", list(FAX_BOOK.keys()), key="tab1_org")
        with rc2:
            receiver_fax = st.text_input("수신 팩스번호", value=FAX_BOOK[selected_org], key="tab1_fax")
        sender_fax = st.text_input("발신 팩스번호", "031-987-7777", key="tab1_sender")
        
        submit_report = st.form_submit_button("통합 문서 생성 및 전송")

    if submit_report:
        if not receiver_fax:
            st.warning("수신번호를 입력하세요.")
        else:
            data = {
                'reg_date': reg_date, 'checkup_date': checkup_date,
                'start_time': start_time, 'end_time': end_time,
                'location': location, 'target': target,
                'count': count, 'doctor_name': doctor_name
            }
            cover_bytes = create_report_pdf(data)
            if cover_bytes:
                merged_bytes = merge_documents(cover_bytes, doctor_name)
                if merged_bytes:
                    st.success("문서 생성 완료")
                    success, msg = send_fax_barobill_real(merged_bytes, receiver_fax, sender_fax)
                    if success: st.success(msg)
                    else: st.error(msg)

# ==========================================
# 탭 2: 변경/취소 신청서 (신규 기능)
# ==========================================
with tab2:
    st.info("💡 변경 사항이 있는 항목만 입력하세요.")
    
    with st.form("fix_form"):
        # 신청 구분
        apply_type = st.radio("신청 구분", ["변경 신청", "취소 신청"], horizontal=True)
        type_code = 'change' if apply_type == "변경 신청" else 'cancel'

        # 입력 테이블 구성
        st.markdown("#### 상세 내용 입력")
        
        # 2열 레이아웃 헤더
        h1, h2 = st.columns(2)
        h1.caption("▼ 변경 전 내용")
        h2.caption("▼ 변경 후 내용")

        # 각 항목별 입력 필드
        # 1. 일시
        r1_1, r1_2 = st.columns(2)
        date_before = r1_1.text_input("일시 (변경 전)")
        date_after = r1_2.text_input("일시 (변경 후)")
        
        # 2. 장소
        r2_1, r2_2 = st.columns(2)
        place_before = r2_1.text_input("장소 (변경 전)")
        place_after = r2_2.text_input("장소 (변경 후)")

        # 3. 대상
        r3_1, r3_2 = st.columns(2)
        target_before = r3_1.text_input("대상 (변경 전)")
        target_after = r3_2.text_input("대상 (변경 후)")

        # 4. 인원 수
        r4_1, r4_2 = st.columns(2)
        count_before = r4_1.text_input("인원 수 (변경 전)")
        count_after = r4_2.text_input("인원 수 (변경 후)")

        # 5. 수행 인력
        r5_1, r5_2 = st.columns(2)
        staff_before = r5_1.text_input("수행 인력 (변경 전)")
        staff_after = r5_2.text_input("수행 인력 (변경 후)")

        # 6. 실시 항목
        r6_1, r6_2 = st.columns(2)
        items_before = r6_1.text_input("실시 항목 (변경 전)")
        items_after = r6_2.text_input("실시 항목 (변경 후)")

        # 7. 기타
        r7_1, r7_2 = st.columns(2)
        etc_before = r7_1.text_input("기타 (변경 전)")
        etc_after = r7_2.text_input("기타 (변경 후)")

        # 취소 사유 (취소 신청일 때만 유효하지만 UI는 보여둠)
        st.markdown("---")
        cancel_reason = st.text_area("취소 사유 (취소 신청 시 작성)")

        st.subheader("발송 정보")
        fc1, fc2 = st.columns(2)
        with fc1:
            fix_org = st.selectbox("수신처(보건소)", list(FAX_BOOK.keys()), key="tab2_org")
        with fc2:
            fix_fax = st.text_input("수신 팩스번호", value=FAX_BOOK[fix_org], key="tab2_fax")
        fix_sender = st.text_input("발신 팩스번호", "031-987-7777", key="tab2_sender")

        submit_fix = st.form_submit_button("변경/취소 신청서 생성 및 전송")

    if submit_fix:
        if not fix_fax:
            st.warning("수신번호를 입력하세요.")
        else:
            fix_data = {
                'type': type_code,
                'date_before': date_before, 'date_after': date_after,
                'place_before': place_before, 'place_after': place_after,
                'target_before': target_before, 'target_after': target_after,
                'count_before': count_before, 'count_after': count_after,
                'staff_before': staff_before, 'staff_after': staff_after,
                'items_before': items_before, 'items_after': items_after,
                'etc_before': etc_before, 'etc_after': etc_after,
                'cancel_reason': cancel_reason
            }
            
            # PDF 생성
            fix_pdf_bytes = create_fix_pdf(fix_data)
            
            if fix_pdf_bytes:
                # 결과 표시 화면
                res1, res2 = st.columns(2)
                with res1:
                    st.success("문서 생성 완료")
                    st.download_button("신청서 다운로드", fix_pdf_bytes, "변경취소신청서.pdf")
                with res2:
                    with st.spinner("팩스 전송 중..."):
                        success, msg = send_fax_barobill_real(fix_pdf_bytes, fix_fax, fix_sender)
                        if success: st.success(msg)
                        else: st.error(msg)
