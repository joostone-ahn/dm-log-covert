"""
FTP DM Log Converter - Flask 웹 서버
FTP 서버의 DM 로그를 자동으로 PCAP으로 변환
"""
import os
import json
import threading
import queue
import tempfile
import shutil
from flask import Flask, render_template, request, jsonify, Response
from ftp_handler import FTPHandler
from converter import (
    check_scat_installed,
    convert_single_file,
    get_vendor_type,
    SUPPORTED_EXTENSIONS
)

# Flask 앱 설정
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/api/status')
def status():
    """시스템 상태 확인"""
    scat_installed = check_scat_installed()
    
    return jsonify({
        'scat_installed': scat_installed,
        'supported_extensions': SUPPORTED_EXTENSIONS
    })


@app.route('/api/ftp/test', methods=['POST'])
def test_ftp_connection():
    """FTP 연결 테스트"""
    data = request.json
    
    host = data.get('host')
    port = data.get('port', 21)
    username = data.get('username')
    password = data.get('password')
    
    if not all([host, username, password]):
        return jsonify({'success': False, 'message': '필수 정보를 입력해주세요'})
    
    ftp = FTPHandler(host, port, username, password)
    success, message = ftp.connect()
    
    if success:
        ftp.disconnect()
    
    return jsonify({'success': success, 'message': message})


@app.route('/api/ftp/directories', methods=['POST'])
def list_ftp_directories():
    """FTP 디렉토리 목록 조회"""
    data = request.json
    
    host = data.get('host')
    port = data.get('port', 21)
    username = data.get('username')
    password = data.get('password')
    path = data.get('path', '/')
    
    if not all([host, username, password]):
        return jsonify({'success': False, 'message': '필수 정보를 입력해주세요'})
    
    ftp = FTPHandler(host, port, username, password)
    success, message = ftp.connect()
    
    if not success:
        return jsonify({'success': False, 'message': message})
    
    directories = ftp.list_directories(path)
    ftp.disconnect()
    
    return jsonify({
        'success': True,
        'current_path': path,
        'directories': directories
    })


@app.route('/api/ftp/files', methods=['POST'])
def list_ftp_files():
    """FTP 디렉토리의 파일 목록 조회"""
    data = request.json
    
    host = data.get('host')
    port = data.get('port', 21)
    username = data.get('username')
    password = data.get('password')
    path = data.get('path', '/')
    
    if not all([host, username, password]):
        return jsonify({'success': False, 'message': '필수 정보를 입력해주세요'})
    
    ftp = FTPHandler(host, port, username, password)
    success, message = ftp.connect()
    
    if not success:
        return jsonify({'success': False, 'message': message})
    
    files = ftp.list_files_in_directory(path, SUPPORTED_EXTENSIONS)
    ftp.disconnect()
    
    # 파일명만 추출
    file_list = []
    for filepath in files:
        filename = os.path.basename(filepath)
        base_name = os.path.splitext(filename)[0]
        pcap_filename = f"{base_name}.pcap"
        
        file_list.append({
            'name': filename,
            'path': filepath,
            'pcap_name': pcap_filename
        })
    
    return jsonify({
        'success': True,
        'path': path,
        'files': file_list,
        'count': len(file_list)
    })


@app.route('/api/ftp/convert', methods=['POST'])
def start_ftp_conversion():
    """FTP 자동 변환 시작"""
    data = request.json
    
    host = data.get('host')
    port = data.get('port', 21)
    username = data.get('username')
    password = data.get('password')
    target_path = data.get('target_path', '/')
    layers = data.get('layers', 'rrc,nas')
    gsmtap_v3 = data.get('gsmtap_v3', True)
    
    # 세션 ID 생성
    import uuid
    session_id = str(uuid.uuid4())
    
    # 진행 상황을 저장할 큐 생성
    progress_queue = queue.Queue()
    
    # 백그라운드에서 변환 실행
    def run_conversion():
        temp_dir = None
        
        try:
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp(prefix='ftp_converter_')
            
            def progress_callback(message):
                progress_queue.put(message)
            
            # FTP 연결
            progress_callback("FTP 서버 연결 중...")
            ftp = FTPHandler(host, port, username, password)
            success, message = ftp.connect()
            
            if not success:
                progress_queue.put(json.dumps({'error': message}))
                return
            
            progress_callback(f"✓ {message}\n")
            
            # 파일 목록 가져오기
            progress_callback(f"디렉토리: {target_path}")
            files = ftp.list_files_in_directory(target_path, SUPPORTED_EXTENSIONS)
            
            if not files:
                progress_callback("변환할 파일이 없습니다")
                progress_queue.put(json.dumps({'done': True, 'result': {
                    'total': 0,
                    'success': 0,
                    'skipped': 0,
                    'failed': 0
                }}))
                ftp.disconnect()
                return
            
            progress_callback(f"✓ 총 {len(files)}개 파일 발견\n")
            
            # 각 파일 처리
            success_count = 0
            skipped_count = 0
            failed_count = 0
            
            for idx, remote_file in enumerate(files, 1):
                filename = os.path.basename(remote_file)
                base_name = os.path.splitext(filename)[0]
                pcap_filename = f"{base_name}.pcap"
                remote_pcap = os.path.join(os.path.dirname(remote_file), pcap_filename).replace('\\', '/')
                
                vendor_type = get_vendor_type(filename)
                
                progress_callback(f"[{idx}/{len(files)}] {remote_file}")
                
                # PCAP 파일이 이미 존재하는지 확인
                if ftp.file_exists(remote_pcap):
                    progress_callback(f"  ⊘ 건너뛰기 (PCAP 파일 이미 존재)")
                    skipped_count += 1
                    continue
                
                # 파일 다운로드
                local_file = os.path.join(temp_dir, filename)
                success, msg = ftp.download_file(remote_file, local_file)
                
                if not success:
                    progress_callback(f"  ✗ 다운로드 실패: {msg}")
                    failed_count += 1
                    continue
                
                # 변환
                local_pcap = os.path.join(temp_dir, pcap_filename)
                result = convert_single_file(
                    local_file,
                    local_pcap,
                    vendor_type,
                    layers,
                    gsmtap_v3
                )
                
                if not result['success']:
                    progress_callback(f"  ✗ 변환 실패: {result['message']}")
                    failed_count += 1
                    # 다운로드한 파일 삭제
                    if os.path.exists(local_file):
                        os.remove(local_file)
                    continue
                
                # PCAP 파일 업로드
                success, msg = ftp.upload_file(local_pcap, remote_pcap)
                
                if success:
                    progress_callback(f"  ✓ 변환 및 업로드 완료")
                    success_count += 1
                else:
                    progress_callback(f"  ✗ 업로드 실패: {msg}")
                    failed_count += 1
                
                # 임시 파일 삭제
                if os.path.exists(local_file):
                    os.remove(local_file)
                if os.path.exists(local_pcap):
                    os.remove(local_pcap)
            
            # FTP 연결 종료
            ftp.disconnect()
            
            # 최종 결과
            final_msg = f"\n=== 변환 완료 ===\n성공: {success_count}\n건너뛰기: {skipped_count}\n실패: {failed_count}"
            progress_callback(final_msg)
            
            progress_queue.put(json.dumps({'done': True, 'result': {
                'total': len(files),
                'success': success_count,
                'skipped': skipped_count,
                'failed': failed_count
            }}))
            
        except Exception as e:
            progress_queue.put(json.dumps({'error': f"오류 발생: {str(e)}"}))
        finally:
            # 임시 디렉토리 삭제
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    # 큐를 전역 딕셔너리에 저장
    if not hasattr(app, 'conversion_queues'):
        app.conversion_queues = {}
    app.conversion_queues[session_id] = progress_queue
    
    # 백그라운드 스레드 시작
    thread = threading.Thread(target=run_conversion)
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})


@app.route('/api/ftp/progress/<session_id>')
def ftp_conversion_progress(session_id):
    """SSE를 통한 실시간 진행 상황 스트리밍"""
    def generate():
        if not hasattr(app, 'conversion_queues') or session_id not in app.conversion_queues:
            yield f"data: {json.dumps({'error': 'Invalid session'})}\n\n"
            return
        
        progress_queue = app.conversion_queues[session_id]
        
        while True:
            try:
                # 큐에서 메시지 가져오기
                message = progress_queue.get(timeout=60)
                
                # JSON 형식인지 확인 (최종 결과 또는 에러)
                if message.startswith('{'):
                    yield f"data: {message}\n\n"
                    break
                else:
                    # 일반 진행 메시지
                    yield f"data: {json.dumps({'message': message})}\n\n"
                    
            except queue.Empty:
                # 타임아웃 시 연결 유지 메시지
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
        
        # 세션 정리
        if session_id in app.conversion_queues:
            del app.conversion_queues[session_id]
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    # scat 설치 확인
    if not check_scat_installed():
        print("경고: scat이 설치되지 않았습니다!")
    else:
        print("✓ scat 설치 확인")
    
    print(f"서버 시작: http://0.0.0.0:9090")
    
    app.run(host='0.0.0.0', port=9090, debug=False)
