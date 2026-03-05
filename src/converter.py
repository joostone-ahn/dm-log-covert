"""
SCAT 변환 로직
- DM 로그 → PCAP 변환 (scat)
"""
import os
import subprocess
from datetime import datetime


# 지원하는 파일 확장자 및 벤더 매핑
EXTENSION_VENDOR_MAP = {
    '.qmdl': 'qc',
    '.hdf': 'qc',
    '.dlf': 'qc',
    '.sdm': 'sec'
}

SUPPORTED_EXTENSIONS = list(EXTENSION_VENDOR_MAP.keys())

# 벤더 타입 표시명
VENDOR_NAMES = {
    'qc': 'Qualcomm',
    'sec': 'Samsung'
}


def get_vendor_type(filename):
    """
    파일 확장자로 벤더 타입 자동 판단
    
    Args:
        filename: 파일명
        
    Returns:
        str: 벤더 타입 ('qc' 또는 'sec'), 알 수 없으면 'qc' 기본값
    """
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_VENDOR_MAP.get(ext, 'qc')


def check_scat_installed():
    """scat 설치 확인"""
    try:
        result = subprocess.run(['scat', '--version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_supported_files(directory):
    """디렉토리에서 지원하는 파일 목록 반환 (하위 디렉토리 제외)"""
    if not os.path.exists(directory):
        return []
    
    files = []
    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            # 파일만 확인 (디렉토리 제외)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(filename)
    except PermissionError:
        pass
    
    return sorted(files)


def convert_single_file(input_path, output_path, vendor_type=None, layers='rrc,nas', gsmtap_v3=True):
    """
    단일 파일을 PCAP으로 변환
    
    Args:
        input_path: 입력 파일 경로
        output_path: 출력 PCAP 파일 경로
        vendor_type: 벤더 타입 ('qc' 또는 'sec'), None이면 자동 판단
        layers: 추출할 레이어 (기본: 'rrc,nas')
        gsmtap_v3: GSMTAPv3 활성화 여부 (기본: True)
    
    Returns:
        dict: {'success': bool, 'message': str, 'output_size': int, 'scat_output': str}
    """
    # 입력 파일 확인
    if not os.path.exists(input_path):
        return {
            'success': False,
            'message': f'입력 파일을 찾을 수 없습니다: {input_path}',
            'output_size': 0,
            'scat_output': ''
        }
    
    # 파일 크기 확인
    input_size = os.path.getsize(input_path)
    if input_size == 0:
        return {
            'success': False,
            'message': '입력 파일이 비어있습니다',
            'output_size': 0,
            'scat_output': ''
        }
    
    # 벤더 타입 자동 판단
    if vendor_type is None:
        filename = os.path.basename(input_path)
        vendor_type = get_vendor_type(filename)
    
    # scat 명령어 구성
    cmd = [
        'scat',
        '-t', vendor_type,
        '-d', input_path,
        '-F', output_path,
        '-L', layers
    ]
    
    # GSMTAPv3 옵션 추가
    if gsmtap_v3:
        cmd.append('-3')
    
    try:
        # scat 실행 (타임아웃 없음 - 큰 파일 지원)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=None
        )
        
        # scat 출력 저장
        scat_output = result.stdout + '\n' + result.stderr
        
        # 변환 실패 확인
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            return {
                'success': False,
                'message': f'scat 변환 실패 (코드: {result.returncode}): {error_msg[:200]}',
                'output_size': 0,
                'scat_output': scat_output
            }
        
        # 출력 파일 확인
        if not os.path.exists(output_path):
            return {
                'success': False,
                'message': 'PCAP 파일이 생성되지 않았습니다',
                'output_size': 0,
                'scat_output': scat_output
            }
        
        output_size = os.path.getsize(output_path)
        if output_size == 0:
            return {
                'success': False,
                'message': '빈 PCAP 파일이 생성되었습니다 (RRC/NAS 메시지 없음)',
                'output_size': 0,
                'scat_output': scat_output
            }
        
        return {
            'success': True,
            'message': f'변환 완료 ({input_size / 1024:.1f}KB → {output_size / 1024:.1f}KB)',
            'output_size': output_size,
            'scat_output': scat_output
        }
    
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'message': '변환 시간 초과',
            'output_size': 0,
            'scat_output': ''
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'변환 중 오류 발생: {str(e)}',
            'output_size': 0,
            'scat_output': ''
        }


def convert_batch(input_dir, output_dir, layers='rrc,nas', gsmtap_v3=True, progress_callback=None):
    """
    디렉토리 내 모든 지원 파일을 일괄 변환
    
    Args:
        input_dir: 입력 디렉토리 경로
        output_dir: 출력 디렉토리 경로
        layers: 추출할 레이어
        gsmtap_v3: GSMTAPv3 활성화 여부
        progress_callback: 진행 상황 콜백 함수 (선택)
    
    Returns:
        dict: {
            'total': int,
            'success': int,
            'failed': int,
            'results': [{'filename': str, 'success': bool, 'message': str}],
            'log': str
        }
    """
    # 지원 파일 목록 가져오기
    files = get_supported_files(input_dir)
    
    if not files:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'results': [],
            'log': '변환할 파일이 없습니다'
        }
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    success_count = 0
    failed_count = 0
    log_lines = []
    
    log_lines.append(f"=== 일괄 변환 시작 ===")
    log_lines.append(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append(f"입력 디렉토리: {input_dir}")
    log_lines.append(f"출력 디렉토리: {output_dir}")
    log_lines.append(f"레이어: {layers}")
    log_lines.append(f"GSMTAPv3: {'활성화' if gsmtap_v3 else '비활성화'}")
    log_lines.append(f"총 파일 수: {len(files)}\n")
    
    # 진행 상황 콜백 호출
    if progress_callback:
        progress_callback('\n'.join(log_lines))
    
    # 각 파일 변환
    for idx, filename in enumerate(files, 1):
        input_path = os.path.join(input_dir, filename)
        
        # 벤더 타입 자동 판단
        vendor_type = get_vendor_type(filename)
        vendor_name = VENDOR_NAMES.get(vendor_type, vendor_type)
        
        # 출력 파일명 생성 (확장자만 .pcap으로 변경)
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}.pcap"
        output_path = os.path.join(output_dir, output_filename)
        
        progress_msg = f"[{idx}/{len(files)}] {filename}\n  벤더: {vendor_name}\n  변환 중..."
        log_lines.append(f"[{idx}/{len(files)}] {filename}")
        log_lines.append(f"  벤더: {vendor_name}")
        
        # 진행 상황 콜백 호출
        if progress_callback:
            progress_callback(progress_msg)
        
        # 변환 실행
        result = convert_single_file(
            input_path,
            output_path,
            vendor_type,
            layers,
            gsmtap_v3
        )
        
        if result['success']:
            success_count += 1
            result_msg = f"  ✓ {result['message']}"
            log_lines.append(result_msg)
        else:
            failed_count += 1
            result_msg = f"  ✗ {result['message']}"
            log_lines.append(result_msg)
        
        # 진행 상황 콜백 호출
        if progress_callback:
            progress_callback(result_msg)
        
        results.append({
            'filename': filename,
            'output_filename': output_filename if result['success'] else None,
            'success': result['success'],
            'message': result['message'],
            'output_size': result['output_size'],
            'vendor': vendor_name
        })
        
        log_lines.append("")
    
    final_msg = f"\n=== 변환 완료 ===\n성공: {success_count}/{len(files)}\n실패: {failed_count}/{len(files)}"
    log_lines.append(f"=== 변환 완료 ===")
    log_lines.append(f"성공: {success_count}/{len(files)}")
    log_lines.append(f"실패: {failed_count}/{len(files)}")
    
    # 최종 결과 콜백 호출
    if progress_callback:
        progress_callback(final_msg)
    
    return {
        'total': len(files),
        'success': success_count,
        'failed': failed_count,
        'results': results,
        'log': '\n'.join(log_lines)
    }
