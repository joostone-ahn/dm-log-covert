#!/usr/bin/env python3
"""
DM Log Converter 로컬 테스트 스크립트
Docker 빌드 전에 로컬에서 변환 기능을 테스트합니다.
"""
import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from converter import (
    check_scat_installed,
    get_supported_files,
    convert_single_file,
    convert_batch,
    SUPPORTED_EXTENSIONS,
    VENDOR_TYPES
)


def print_header(text):
    """헤더 출력"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text):
    """성공 메시지 출력"""
    print(f"✓ {text}")


def print_error(text):
    """에러 메시지 출력"""
    print(f"✗ {text}")


def print_info(text):
    """정보 메시지 출력"""
    print(f"ℹ {text}")


def check_environment():
    """환경 확인"""
    print_header("환경 확인")
    
    # Python 버전
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_info(f"Python 버전: {python_version}")
    
    # scat 설치 확인
    print("\nscat 설치 확인 중...")
    if check_scat_installed():
        print_success("scat이 설치되어 있습니다")
        return True
    else:
        print_error("scat이 설치되지 않았습니다")
        print("\n설치 방법:")
        print("  pip install git+https://github.com/fgsect/scat.git")
        return False


def check_directories():
    """디렉토리 확인 및 생성"""
    print_header("디렉토리 확인")
    
    input_dir = './input'
    output_dir = './output'
    
    # 입력 디렉토리
    if os.path.exists(input_dir):
        print_success(f"입력 디렉토리 존재: {input_dir}")
    else:
        os.makedirs(input_dir)
        print_info(f"입력 디렉토리 생성: {input_dir}")
    
    # 출력 디렉토리
    if os.path.exists(output_dir):
        print_success(f"출력 디렉토리 존재: {output_dir}")
    else:
        os.makedirs(output_dir)
        print_info(f"출력 디렉토리 생성: {output_dir}")
    
    return True


def list_input_files():
    """입력 파일 목록 표시"""
    print_header("입력 파일 확인")
    
    input_dir = './input'
    files = get_supported_files(input_dir)
    
    if not files:
        print_error(f"{input_dir} 디렉토리에 변환할 파일이 없습니다")
        print(f"\n지원 형식: {', '.join(SUPPORTED_EXTENSIONS)}")
        return []
    
    print_success(f"{len(files)}개의 파일 발견:\n")
    for idx, filename in enumerate(files, 1):
        filepath = os.path.join(input_dir, filename)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        ext = os.path.splitext(filename)[1]
        print(f"  {idx}. {filename}")
        print(f"     크기: {size_mb:.2f} MB, 형식: {ext}")
    
    return files


def test_single_conversion(files):
    """단일 파일 변환 테스트"""
    print_header("단일 파일 변환 테스트")
    
    if not files:
        print_error("변환할 파일이 없습니다")
        return
    
    # 파일 선택
    print("파일 목록:")
    for idx, f in enumerate(files, 1):
        print(f"  {idx}. {f}")
    
    try:
        file_idx = int(input("\n변환할 파일 번호를 입력하세요: ")) - 1
        if file_idx < 0 or file_idx >= len(files):
            print_error("잘못된 번호입니다")
            return
    except (ValueError, KeyboardInterrupt):
        print("\n취소되었습니다")
        return
    
    filename = files[file_idx]
    
    # 벤더 타입 선택
    print("\n벤더 타입:")
    print("  1. Qualcomm (qc)")
    print("  2. Samsung (sec)")
    
    try:
        vendor_choice = input("벤더 타입을 선택하세요 (기본값: 1): ").strip() or "1"
        vendor_type = 'qc' if vendor_choice == '1' else 'sec'
    except KeyboardInterrupt:
        print("\n취소되었습니다")
        return
    
    # 변환 실행
    input_path = os.path.join('./input', filename)
    output_filename = os.path.splitext(filename)[0] + '.pcap'
    output_path = os.path.join('./output', output_filename)
    
    print(f"\n변환 중...")
    print(f"  입력: {input_path}")
    print(f"  출력: {output_path}")
    print(f"  벤더: {VENDOR_TYPES[vendor_type]}")
    
    result = convert_single_file(
        input_path,
        output_path,
        vendor_type=vendor_type,
        layers='rrc,nas',
        gsmtap_v3=False
    )
    
    print()
    if result['success']:
        print_success(result['message'])
        print(f"\n출력 파일: {output_path}")
    else:
        print_error(result['message'])


def test_batch_conversion(files):
    """일괄 변환 테스트"""
    print_header("일괄 변환 테스트")
    
    if not files:
        print_error("변환할 파일이 없습니다")
        return
    
    print(f"{len(files)}개의 파일을 일괄 변환합니다:")
    for f in files:
        print(f"  - {f}")
    
    # 벤더 타입 선택
    print("\n벤더 타입:")
    print("  1. Qualcomm (qc)")
    print("  2. Samsung (sec)")
    
    try:
        vendor_choice = input("벤더 타입을 선택하세요 (기본값: 1): ").strip() or "1"
        vendor_type = 'qc' if vendor_choice == '1' else 'sec'
        
        confirm = input(f"\n{len(files)}개 파일을 변환하시겠습니까? (y/n): ").strip().lower()
        if confirm != 'y':
            print("취소되었습니다")
            return
    except KeyboardInterrupt:
        print("\n취소되었습니다")
        return
    
    # 일괄 변환 실행
    print(f"\n일괄 변환 시작...\n")
    
    result = convert_batch(
        './input',
        './output',
        vendor_type=vendor_type,
        layers='rrc,nas',
        gsmtap_v3=False
    )
    
    # 결과 출력
    print("\n" + "="*60)
    print(result['log'])
    print("="*60)


def main():
    """메인 함수"""
    print_header("DM Log Converter 로컬 테스트")
    
    # 1. 환경 확인
    if not check_environment():
        return
    
    # 2. 디렉토리 확인
    if not check_directories():
        return
    
    # 3. 입력 파일 확인
    files = list_input_files()
    
    if not files:
        print("\n테스트를 종료합니다.")
        print("변환할 파일을 ./input 디렉토리에 넣어주세요.")
        return
    
    # 4. 테스트 메뉴
    while True:
        print_header("테스트 메뉴")
        print("1. 단일 파일 변환 테스트")
        print("2. 일괄 변환 테스트")
        print("3. 파일 목록 새로고침")
        print("4. 종료")
        
        try:
            choice = input("\n선택하세요 (1-4): ").strip()
            
            if choice == '1':
                test_single_conversion(files)
            elif choice == '2':
                test_batch_conversion(files)
            elif choice == '3':
                files = list_input_files()
            elif choice == '4':
                print("\n테스트를 종료합니다.")
                break
            else:
                print_error("잘못된 선택입니다")
        
        except KeyboardInterrupt:
            print("\n\n테스트를 종료합니다.")
            break
        except Exception as e:
            print_error(f"오류 발생: {str(e)}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
    except Exception as e:
        print_error(f"예상치 못한 오류: {str(e)}")
        import traceback
        traceback.print_exc()
