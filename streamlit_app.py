import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
from pypdf import PdfWriter, PdfReader
import base64
import os
import ftplib # FTP 업로드용 표준 라이브러리
from zeep import Client

# --- 설정 및 상수 ---
FONT_PATH = "NanumGothic.ttf"
TEMPLATE_PATH = "background.png"
TEMPLATE_FIX_PATH = "background_fix001.png"

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
# 테스트용 WSDL: https://testws.baroservice.com/FAX.asmx?WSDL
# 운영용 WSDL: https://ws.baroservice.com/FAX.asmx?WSDL
BAROBILL_WSDL_URL = "https://testws.baroservice.com/FAX.asmx?WSDL"

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
        
        if data['type'] == 'change':
            add_text_to_image(draw, "V", (550, 85), font_size=20, color="red")
        else:
            add_text_to_image(draw, "V", (550, 130), font_size=20, color="red")

        row_start_y = 950
        row_gap = 100
        col_before_x = 350
        col_after_x = 900

        items = ['date', 'place', 'target', 'count', 'staff', 'items', 'etc']
        
        for i, item in enumerate(items):
            y_pos = row_start_y + (i * row_gap)
            before_val = data.get(f'{item}_before', '')
            after_val = data.get(f'{item}_after', '')
            
            add_text_to_image(draw, before_val, (col_before_x, y_pos))
            add_text_to_image(draw, after_val, (col_after_x, y_pos))

        if data['type'] == 'cancel':
            add_text_to_image(draw, data['cancel_reason'], (300, 1750))

        today = datetime.now()
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
    """문서 병합 로직"""
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

# =========================================================
# FTP 업로드 로직 (가이드 반영: Passive Mode & 특정 포트)
# =========================================================
def upload_file_to_ftp(pdf_bytes, filename):
    """생성된 PDF를 바로빌 FTP 서버에 업로드 (Passive Mode)"""
    try:
        ftp_host = st.secrets["BAROBILL_FTP_HOST"]
        ftp_port = int(st.secrets["BAROBILL_FTP_PORT"]) # 9030 or 9031
        ftp_id = st.secrets["BAROBILL_FTP_ID"]
        ftp_pwd = st.secrets["BAROBILL_FTP_PWD"]
        
        # 1. FTP 객체 생성
        ftp = ftplib.FTP()
        
        # 2. 특정 포트로 접속 (connect 사용)
        ftp.connect(ftp_host, ftp_port)
        
        # 3. 로그인
        ftp.login(user=ftp_id, passwd=ftp_pwd)
        
        # 4. Passive Mode 설정 (가이드 준수: 필수 사항)
        ftp.set_pasv(True)
        
        # 5. 바이너리 모드로 파일 업로드
        ftp.storbinary(f"STOR {filename}", BytesIO(pdf_bytes))
        
        # 6. 종료
        ftp.quit()
            
        return True, "FTP 업로드 성공"
    except Exception as e:
        return False, f"FTP 업로드 실패: {e}"

def send_fax_from_ftp_real(filename, receiver_num, sender_num):
    """FTP에 업로드된 파일을 바로빌 API(SendFaxFromFTP)를 통해 전송 요청"""
    try:
        if "BAROBILL_CERT_KEY" not in st.secrets:
            return False, "API 키(Secrets)가 설정되지 않았습니다."
            
        cert_key = st.secrets["BAROBILL_CERT_KEY"]
        corp_num = st.secrets["BAROBILL_CORP_NUM"]
        sender_id = st.secrets["BAROBILL_ID"]

        client = Client(BAROBILL_WSDL_URL)
        
        # SendFaxFromFTP 호출
        result = client.service.SendFaxFromFTP(
            CERTKEY=cert_key,
            CorpNum=corp_num,
            SenderID=sender_id,
            FileName=filename,          # FTP에 올린 파일명 그대로 사용
            FromNumber=sender_num.replace("-", ""),
            ToNumber=receiver_num.replace("-", ""),
            ReceiveCorp="보건소",
            ReceiveName="담당자",
            SendDT="",                  # 빈값이면 즉시 전송
            RefKey=""
        )
        
        if int(result) < 0:
            return False, f"전송 실패 (에러코드: {result})"
        else:
            return True, f"전송 접수 완료 (접수번호: {result})"

    except Exception as e:
        return False, f"API 통신 오류: {str(e)}"

# =========================================================
# UI 메인
# =========================================================
st.set_page_config(page_title="출장검진 팩스 시스템", layout="wide")
st.title("🏥 뉴고려병원 출장검진 팩스 시스템")

tab1, tab2 = st.tabs(["📑 출장검진 신고서", "📝 변경/취소 신청서"])

# 탭 1: 기존 출장검진 신고서
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
                    st.success("1. 문서 생성 완료")
                    
                    # 파일명 생성 (영문/숫자 조합 권장)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"Report_{timestamp}.pdf"
                    
                    with st.spinner(f"2. 바로빌 FTP 업로드 중... (파일명: {filename})"):
                        ftp_success, ftp_msg = upload_file_to_ftp(merged_bytes, filename)
                    
                    if ftp_success:
                        with st.spinner("3. 팩스 전송 요청 중..."):
                            success, msg = send_fax_from_ftp_real(filename, receiver_fax, sender_fax)
                            if success: st.success(msg)
                            else: st.error(msg)
                    else:
                        st.error(ftp_msg)

# 탭 2: 변경/취소 신청서
with tab2:
    st.info("💡 변경 사항이 있는 항목만 입력하세요.")
    
    with st.form("fix_form"):
        apply_type = st.radio("신청 구분", ["변경 신청", "취소 신청"], horizontal=True)
        type_code = 'change' if apply_type == "변경 신청" else 'cancel'

        st.markdown("#### 상세 내용 입력")
        h1, h2 = st.columns(2)
        h1.caption("▼ 변경 전 내용")
        h2.caption("▼ 변경 후 내용")

        r1_1, r1_2 = st.columns(2)
        date_before = r1_1.text_input("일시 (변경 전)")
        date_after = r1_2.text_input("일시 (변경 후)")
        
        r2_1, r2_2 = st.columns(2)
        place_before = r2_1.text_input("장소 (변경 전)")
        place_after = r2_2.text_input("장소 (변경 후)")

        r3_1, r3_2 = st.columns(2)
        target_before = r3_1.text_input("대상 (변경 전)")
        target_after = r3_2.text_input("대상 (변경 후)")

        r4_1, r4_2 = st.columns(2)
        count_before = r4_1.text_input("인원 수 (변경 전)")
        count_after = r4_2.text_input("인원 수 (변경 후)")

        r5_1, r5_2 = st.columns(2)
        staff_before = r5_1.text_input("수행 인력 (변경 전)")
        staff_after = r5_2.text_input("수행 인력 (변경 후)")

        r6_1, r6_2 = st.columns(2)
        items_before = r6_1.text_input("실시 항목 (변경 전)")
        items_after = r6_2.text_input("실시 항목 (변경 후)")

        r7_1, r7_2 = st.columns(2)
        etc_before = r7_1.text_input("기타 (변경 전)")
        etc_after = r7_2.text_input("기타 (변경 후)")

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
            
            fix_pdf_bytes = create_fix_pdf(fix_data)
            
            if fix_pdf_bytes:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"FixRequest_{timestamp}.pdf"
                
                with st.spinner(f"FTP 업로드 중... (파일명: {filename})"):
                    ftp_success, ftp_msg = upload_file_to_ftp(fix_pdf_bytes, filename)
                
                if ftp_success:
                    with st.spinner("팩스 전송 요청 중..."):
                        success, msg = send_fax_from_ftp_real(filename, fix_fax, fix_sender)
                        if success: st.success(msg)
                        else: st.error(msg)
                else:
                    st.error(ftp_msg)
