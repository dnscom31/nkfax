import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
from pypdf import PdfWriter, PdfReader
import base64
import os
import ftplib
from zeep import Client

# --- 설정 및 상수 ---
FONT_PATH = "NanumGothic.ttf"
TEMPLATE_PATH = "background-001.png"             # 건강검진 신고서 배경
TEMPLATE_FIX_PATH = "background_fix001-001.png"  # 변경/취소 신청서 배경

# 고정 첨부 파일
FILE_LICENSE = "개설허가증.pdf"
FILE_SPECIAL_CERT = "특수의료기관지정서.jpg"

# 의사별 면허증 매칭
DOCTOR_MAP = {
    "선택안함": None,
    "유민상": "유민상.pdf",
    "최윤범": "최윤범.pdf",
    "안형숙": "안형숙.pdf"
}

# --- 바로빌 API 설정 ---
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

# --- 팩스 번호 업데이트 콜백 ---
def update_fax_tab1():
    if st.session_state.tab1_org in FAX_BOOK:
        st.session_state.tab1_fax = FAX_BOOK[st.session_state.tab1_org]

def update_fax_tab2():
    if st.session_state.tab2_org in FAX_BOOK:
        st.session_state.tab2_fax = FAX_BOOK[st.session_state.tab2_org]

def add_text_to_image(draw, text, position, font_size=20, color="black"):
    if not text: return
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    draw.text(position, str(text), fill=color, font=font)

def create_report_pdf(data):
    """(탭1) 건강검진 신고서 생성"""
    try:
        image = Image.open(TEMPLATE_PATH).convert("RGB")
        image = image.resize((1240, 1754))
        draw = ImageDraw.Draw(image)
        
        # 1. 목적 (일시 바로 위)
        add_text_to_image(draw, data['purpose'], (320, 455))

        # 2. 일시/시간/장소/대상/인원/의사
        target_date_str = data['checkup_date'].strftime("%Y년 %m월 %d일")
        add_text_to_image(draw, target_date_str, (320, 490))
        time_str = f"{data['start_time'].strftime('%H:%M')} ~ {data['end_time'].strftime('%H:%M')}"
        add_text_to_image(draw, time_str, (320, 530))
        add_text_to_image(draw, data['location'], (750, 490))
        add_text_to_image(draw, data['target'], (320, 565))
        add_text_to_image(draw, f"{data['count']}명", (930, 565))
        add_text_to_image(draw, data['doctor_name'], (620, 755))
        
        # 3. 체크박스 자동화
        purpose = data['purpose']
        check_national = False
        check_other = False
        
        if purpose == "출장 일반검진":
            check_national = True
        elif purpose == "출장 일반검진+특수검진":
            check_national = True
            check_other = True
        else: # 특수검진 or 보건예방
            check_other = True
            
        if check_national:
            add_text_to_image(draw, "V", (252, 665), font_size=22, color="red")
        if check_other:
            add_text_to_image(draw, "V", (252, 695), font_size=22, color="red")

        # 4. 하단 날짜 (유태전 서명 위)
        today = datetime.now()
        add_text_to_image(draw, str(today.year), (870, 1032), font_size=18)
        add_text_to_image(draw, str(today.month), (980, 1032), font_size=18)
        add_text_to_image(draw, str(today.day), (1070, 1032), font_size=18)

        pdf_buffer = BytesIO()
        image.save(pdf_buffer, format="PDF", resolution=150.0)
        return pdf_buffer.getvalue()
    except Exception as e:
        st.error(f"신고서 표지 생성 오류: {e}")
        return None

def create_fix_pdf(data):
    """(탭2) 변경/취소 신청서 생성"""
    try:
        image = Image.open(TEMPLATE_FIX_PATH).convert("RGB")
        image = image.resize((1240, 1754))
        draw = ImageDraw.Draw(image)
        
        # [체크박스] - 위치 수정하려면 여기 좌표를 변경하세요
        if data['type'] == 'change':
            add_text_to_image(draw, "V", (685, 165), font_size=30, color="red")
        else:
            add_text_to_image(draw, "V", (685, 218), font_size=30, color="red")

        # [테이블 행 좌표]
        rows_y = {
            'date': 700,
            'place': 775,
            'target': 845,
            'count': 905,
            'staff': 970,
            'items': 1050,
            'etc': 1120
        }
        
        col_before_x = 400
        col_after_x = 850
        
        # 일반 항목 입력
        items = ['date', 'place', 'target', 'count', 'items', 'etc']
        for item in items:
            y_pos = rows_y[item]
            before_val = data.get(f'{item}_before', '')
            after_val = data.get(f'{item}_after', '')
            if before_val: add_text_to_image(draw, before_val, (col_before_x, y_pos))
            if after_val: add_text_to_image(draw, after_val, (col_after_x, y_pos))

        # 수행 인력 (Staff)
        staff_y = rows_y['staff']
        if data['staff_before'] and data['staff_before'] != "선택안함":
             add_text_to_image(draw, data['staff_before'], (col_before_x, staff_y))
        
        if data['staff_after'] and data['staff_after'] != "선택안함":
             add_text_to_image(draw, data['staff_after'], (col_after_x, staff_y))

        # 취소 사유
        if data['type'] == 'cancel':
            add_text_to_image(draw, data['cancel_reason'], (300, 1300))

        # [하단 날짜]
        today = datetime.now()
        add_text_to_image(draw, str(today.year), (870, 1430), font_size=22)
        add_text_to_image(draw, str(today.month), (990, 1430), font_size=22)
        add_text_to_image(draw, str(today.day), (1060, 1430), font_size=22)

        pdf_buffer = BytesIO()
        image.save(pdf_buffer, format="PDF", resolution=150.0)
        return pdf_buffer.getvalue()
    except Exception as e:
        st.error(f"변경신청서 생성 오류: {e}")
        return None

def merge_documents_report(cover_pdf_bytes, doctor_name):
    """(탭1) 신고서용 병합"""
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

def merge_documents_fix(cover_pdf_bytes, doctor_name_after):
    """(탭2) 변경신청서용 병합"""
    merger = PdfWriter()
    try:
        merger.append(PdfReader(BytesIO(cover_pdf_bytes)))
        
        if doctor_name_after and doctor_name_after != "선택안함":
            doc_file = DOCTOR_MAP.get(doctor_name_after)
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
        st.error(f"문서 병합 오류(변경신청): {e}")
        return None

def upload_file_to_ftp(pdf_bytes, filename):
    """FTP 업로드"""
    try:
        ftp_host = st.secrets["BAROBILL_FTP_HOST"]
        ftp_port = int(st.secrets["BAROBILL_FTP_PORT"])
        ftp_id = st.secrets["BAROBILL_FTP_ID"]
        ftp_pwd = st.secrets["BAROBILL_FTP_PWD"]
        
        ftp = ftplib.FTP()
        ftp.connect(ftp_host, ftp_port)
        
        # [핵심 수정] 한글 파일명 전송을 위해 인코딩을 CP949(EUC-KR)로 강제 설정
        ftp.encoding = "cp949"
        
        ftp.login(user=ftp_id, passwd=ftp_pwd)
        ftp.set_pasv(True)
        ftp.storbinary(f"STOR {filename}", BytesIO(pdf_bytes))
        ftp.quit()
        return True, "FTP 업로드 성공"
    except Exception as e:
        return False, f"FTP 업로드 실패: {e}"

def send_fax_from_ftp_real(filename, receiver_num, sender_num):
    """바로빌 전송"""
    try:
        if "BAROBILL_CERT_KEY" not in st.secrets:
            return False, "API 키(Secrets)가 설정되지 않았습니다."
            
        cert_key = st.secrets["BAROBILL_CERT_KEY"]
        corp_num = st.secrets["BAROBILL_CORP_NUM"]
        sender_id = st.secrets["BAROBILL_ID"]

        client = Client(BAROBILL_WSDL_URL)
        
        result = client.service.SendFaxFromFTP(
            CERTKEY=cert_key,
            CorpNum=corp_num,
            SenderID=sender_id,
            FileName=filename,
            FromNumber=sender_num.replace("-", ""),
            ToNumber=receiver_num.replace("-", ""),
            ReceiveCorp="보건소",
            ReceiveName="담당자",
            SendDT="",
            RefKey=""
        )
        
        try:
            if int(result) < 0:
                return False, f"전송 실패 (에러코드: {result})"
        except ValueError:
            pass
            
        return True, f"전송 접수 완료 (접수번호: {result})"

    except Exception as e:
        return False, f"API 통신 오류: {str(e)}"

# --- UI 메인 ---
st.set_page_config(page_title="출장검진 팩스 시스템", layout="wide")
st.title("🏥 뉴고려병원 출장검진 팩스 시스템")

# Session State 초기화
if 't1_pdf' not in st.session_state: st.session_state['t1_pdf'] = None
if 't1_meta' not in st.session_state: st.session_state['t1_meta'] = {}
if 't2_pdf' not in st.session_state: st.session_state['t2_pdf'] = None
if 't2_meta' not in st.session_state: st.session_state['t2_meta'] = {}

# 팩스번호 상태 초기화
if 'tab1_fax' not in st.session_state: st.session_state.tab1_fax = ""
if 'tab2_fax' not in st.session_state: st.session_state.tab2_fax = ""

tab1, tab2 = st.tabs(["📑 출장검진 신고서", "📝 변경/취소 신청서"])

# 탭 1 (일반 버튼 사용, on_change 적용)
with tab1:
    st.subheader("1. 신고서 내용 작성")
    
    purpose_options = [
        "출장 일반검진+특수검진", 
        "출장 일반검진", 
        "출장 특수검진", 
        "보건예방사업검진(초음파,골밀도,맥파,심전도)"
    ]
    purpose = st.selectbox("검진 목적", purpose_options)

    c1, c2 = st.columns(2)
    with c1:
        checkup_date = st.date_input("검진 일시", datetime.now())
        start_time = st.time_input("시작 시간", datetime.strptime("07:30", "%H:%M"))
        end_time = st.time_input("종료 시간", datetime.strptime("12:00", "%H:%M"))
    with c2:
        location = st.text_input("장소", "주소입력")
        target = st.text_input("대상", "업체명 입력")
        count = st.number_input("인원 수", value=50)
        doctor_name = st.selectbox("담당 의사", ["유민상", "최윤범", "안형숙"])

    st.markdown("---")
    st.subheader("2. 발송 정보")
    rc1, rc2 = st.columns(2)
    with rc1:
        selected_org = st.selectbox("수신처(보건소)", list(FAX_BOOK.keys()), key="tab1_org", on_change=update_fax_tab1)
    with rc2:
        receiver_fax = st.text_input("수신 팩스번호", key="tab1_fax")
    sender_fax = st.text_input("발신 팩스번호", "031-987-7777", key="tab1_sender")
    
    submit_preview = st.button("1단계: 문서 생성 및 미리보기", key="btn_preview_1")

    if submit_preview:
        if not receiver_fax:
            st.warning("수신번호를 입력하세요.")
        else:
            data = {
                'purpose': purpose,
                'checkup_date': checkup_date,
                'start_time': start_time, 'end_time': end_time,
                'location': location, 'target': target,
                'count': count, 'doctor_name': doctor_name
            }
            cover_bytes = create_report_pdf(data)
            if cover_bytes:
                merged_bytes = merge_documents_report(cover_bytes, doctor_name)
                if merged_bytes:
                    target_name = data['target'].replace(" ", "_") if data['target'] else "Unknown"
                    filename = f"{target_name}_출장신고서_{datetime.now().strftime('%Y%m%d')}.pdf"
                    
                    st.session_state['t1_pdf'] = merged_bytes
                    st.session_state['t1_meta'] = {
                        'receiver': receiver_fax,
                        'sender': sender_fax,
                        'filename': filename
                    }
                    st.success("문서가 생성되었습니다. 아래에서 내용을 확인하고 전송하세요.")
    
    if st.session_state['t1_pdf']:
        st.markdown("### 3. 미리보기 및 전송")
        col_view, col_send = st.columns([1, 1])
        with col_view:
            st.download_button(
                label="📥 생성된 PDF 다운로드 (미리보기)",
                data=st.session_state['t1_pdf'],
                file_name=st.session_state['t1_meta']['filename'],
                mime="application/pdf",
                use_container_width=True
            )
        with col_send:
            if st.button("🚀 팩스 전송하기 (최종)", key="send_btn_tab1", use_container_width=True):
                meta = st.session_state['t1_meta']
                pdf_bytes = st.session_state['t1_pdf']
                with st.spinner(f"전송 진행 중... ({meta['filename']})"):
                    ftp_success, ftp_msg = upload_file_to_ftp(pdf_bytes, meta['filename'])
                    if ftp_success:
                        success, msg = send_fax_from_ftp_real(meta['filename'], meta['receiver'], meta['sender'])
                        if success:
                            st.balloons()
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.error(ftp_msg)

# 탭 2 (일반 버튼 사용, on_change 적용)
with tab2:
    st.info("💡 변경 사항이 있는 항목만 입력하세요.")
    
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
    doctor_list = ["선택안함", "유민상", "최윤범", "안형숙"]
    staff_before = r5_1.selectbox("수행 인력 (변경 전)", doctor_list)
    staff_after = r5_2.selectbox("수행 인력 (변경 후)", doctor_list)

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
        fix_org = st.selectbox("수신처(보건소)", list(FAX_BOOK.keys()), key="tab2_org", on_change=update_fax_tab2)
    with fc2:
        fix_fax = st.text_input("수신 팩스번호", key="tab2_fax")
    fix_sender = st.text_input("발신 팩스번호", "031-987-7777", key="tab2_sender")

    submit_fix_preview = st.button("1단계: 문서 생성 및 미리보기", key="btn_preview_2")

    if submit_fix_preview:
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
                merged_bytes = merge_documents_fix(fix_pdf_bytes, staff_after)
                if merged_bytes:
                    target_name = fix_data['target_before'].replace(" ", "_") if fix_data['target_before'] else "Unknown"
                    filename = f"{target_name}_변경취소신청서_{datetime.now().strftime('%Y%m%d')}.pdf"

                    st.session_state['t2_pdf'] = merged_bytes
                    st.session_state['t2_meta'] = {
                        'receiver': fix_fax,
                        'sender': fix_sender,
                        'filename': filename
                    }
                    st.success("문서가 생성되었습니다. 아래에서 내용을 확인하고 전송하세요.")

    if st.session_state['t2_pdf']:
        st.markdown("### 3. 미리보기 및 전송")
        col_view2, col_send2 = st.columns([1, 1])
        with col_view2:
            st.download_button(
                label="📥 생성된 PDF 다운로드 (미리보기)",
                data=st.session_state['t2_pdf'],
                file_name=st.session_state['t2_meta']['filename'],
                mime="application/pdf",
                use_container_width=True
            )
        with col_send2:
            if st.button("🚀 팩스 전송하기 (최종)", key="send_btn_tab2", use_container_width=True):
                meta = st.session_state['t2_meta']
                pdf_bytes = st.session_state['t2_pdf']
                with st.spinner(f"전송 진행 중... ({meta['filename']})"):
                    ftp_success, ftp_msg = upload_file_to_ftp(pdf_bytes, meta['filename'])
                    if ftp_success:
                        success, msg = send_fax_from_ftp_real(meta['filename'], meta['receiver'], meta['sender'])
                        if success:
                            st.balloons()
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.error(ftp_msg)
