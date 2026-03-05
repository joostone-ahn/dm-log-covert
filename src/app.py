"""
DM Log Converter - Flask 웹 서버
DM 로그를 PCAP으로 변환하는 웹 인터페이스
"""
import os
import json
import threading
import queue
from flask import Flask, render_template, request, jsonify, Response
from converter import (
    check_scat_installed,
    get_supported_files,
    convert_batch,
    get_vendor_type,
    SUPPORTED_EXTENSIONS,
    VENDOR_NAMES
)

# Flask 앱 설정 (templates 디렉토리 경로 지정)
# src 디렉토리에서 실행되므로 상위 디렉토리의 templates 사용
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

# 설정
# Docker 환경에서는 /logs 사용
# 로컬 환경에서는 프로젝트 루트의 logs 사용
if os.environ.get('LOGS_DIR'):
    LOGS_DIR = os.environ.get('LOGS_DIR')
else:
    # 로컬 환경: src 디렉토리 기준으로 상위의 logs 사용
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    LOGS_DIR = os.path.join(project_root, 'logs')

# 입력/출력 디렉토리는 동일
INPUT_DIR = LOGS_DIR
OUTPUT_DIR = LOGS_DIR


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
        'logs_dir': LOGS_DIR,
        'supported_extensions': SUPPORTED_EXTENSIONS
    })


@app.route('/api/files')
def list_files():
    """로그 디렉토리의 파일 목록 조회"""
    files = get_supported_files(INPUT_DIR)
    
    # 파일 정보 추가
    file_info = []
    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        size = os.path.getsize(filepath)
        ext = os.path.splitext(filename)[1].lower()
        vendor_type = get_vendor_type(filename)
        vendor_name = VENDOR_NAMES.get(vendor_type, vendor_type)
        
        file_info.append({
            'name': filename,
            'size': size,
            'size_mb': round(size / (1024 * 1024), 2),
            'extension': ext,
            'vendor': vendor_name
        })
    
    return jsonify({
        'total': len(file_info),
        'files': file_info
    })


@app.route('/api/convert/batch', methods=['POST'])
def convert_batch_route():
    """일괄 변환 시작 (세션 ID 반환)"""
    data = request.json
    
    layers = data.get('layers', 'rrc,nas')
    gsmtap_v3 = data.get('gsmtap_v3', True)
    
    # 세션 ID 생성
    import uuid
    session_id = str(uuid.uuid4())
    
    # 진행 상황을 저장할 큐 생성
    progress_queue = queue.Queue()
    
    # 백그라운드에서 변환 실행
    def run_conversion():
        def progress_callback(message):
            progress_queue.put(message)
        
        try:
            result = convert_batch(
                INPUT_DIR,
                OUTPUT_DIR,
                layers,
                gsmtap_v3,
                progress_callback
            )
            # 최종 결과 전송
            progress_queue.put(json.dumps({'done': True, 'result': result}))
        except Exception as e:
            progress_queue.put(json.dumps({'error': str(e)}))
    
    # 큐를 전역 딕셔너리에 저장
    if not hasattr(app, 'conversion_queues'):
        app.conversion_queues = {}
    app.conversion_queues[session_id] = progress_queue
    
    # 백그라운드 스레드 시작
    thread = threading.Thread(target=run_conversion)
    thread.daemon = True
    thread.start()
    
    return jsonify({'session_id': session_id})


@app.route('/api/convert/progress/<session_id>')
def conversion_progress(session_id):
    """SSE를 통한 실시간 진행 상황 스트리밍"""
    def generate():
        if not hasattr(app, 'conversion_queues') or session_id not in app.conversion_queues:
            yield f"data: {json.dumps({'error': 'Invalid session'})}\n\n"
            return
        
        progress_queue = app.conversion_queues[session_id]
        
        while True:
            try:
                # 큐에서 메시지 가져오기 (타임아웃 60초)
                message = progress_queue.get(timeout=60)
                
                # JSON 형식인지 확인 (최종 결과 또는 에러)
                if message.startswith('{'):
                    yield f"data: {message}\n\n"
                    # 변환 완료 또는 에러 시 종료
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


@app.route('/api/convert/batch_old', methods=['POST'])
def convert_batch_old():
    """일괄 변환 (이전 방식 - 호환성 유지)"""
    data = request.json
    
    layers = data.get('layers', 'rrc,nas')
    gsmtap_v3 = data.get('gsmtap_v3', True)
    
    # 일괄 변환 실행
    result = convert_batch(
        INPUT_DIR,
        OUTPUT_DIR,
        layers,
        gsmtap_v3
    )
    
    return jsonify(result)


if __name__ == '__main__':
    # 디렉토리 존재 확인
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # scat 설치 확인
    if not check_scat_installed():
        print("경고: scat이 설치되지 않았습니다!")
    else:
        print("✓ scat 설치 확인")
    
    print(f"로그 디렉토리: {LOGS_DIR}")
    print(f"서버 시작: http://0.0.0.0:9090")
    
    app.run(host='0.0.0.0', port=9090, debug=False)
