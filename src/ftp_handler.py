"""
FTP 서버 연결 및 파일 처리
"""
import os
import ftplib
from datetime import datetime


class FTPHandler:
    """FTP 서버 연결 및 파일 관리"""
    
    def __init__(self, host, port, username, password):
        """
        FTP 핸들러 초기화
        
        Args:
            host: FTP 서버 호스트
            port: FTP 서버 포트
            username: 사용자명
            password: 비밀번호
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ftp = None
        
    def connect(self):
        """FTP 서버 연결"""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.username, self.password)
            return True, "FTP 연결 성공"
        except Exception as e:
            return False, f"FTP 연결 실패: {str(e)}"
    
    def disconnect(self):
        """FTP 서버 연결 종료"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                self.ftp.close()
    
    def list_directories(self, path="/"):
        """
        디렉토리 목록 가져오기 (재귀 없음)
        
        Args:
            path: 탐색할 경로
            
        Returns:
            list: 디렉토리 정보 리스트 [{'name': str, 'path': str}]
        """
        directories = []
        
        try:
            items = []
            self.ftp.cwd(path)
            self.ftp.retrlines('LIST', items.append)
            
            for item in items:
                parts = item.split()
                if len(parts) < 9:
                    continue
                
                permissions = parts[0]
                name = ' '.join(parts[8:])
                
                # . 과 .. 제외
                if name in ['.', '..']:
                    continue
                
                # 디렉토리만 추가
                if permissions.startswith('d'):
                    full_path = os.path.join(path, name).replace('\\', '/')
                    directories.append({
                        'name': name,
                        'path': full_path
                    })
            
        except Exception as e:
            print(f"디렉토리 목록 오류 ({path}): {str(e)}")
        
        return directories
    
    def list_files_in_directory(self, path="/", extensions=None):
        """
        특정 디렉토리의 파일 목록 가져오기 (하위 디렉토리 제외)
        
        Args:
            path: 디렉토리 경로
            extensions: 필터링할 확장자 리스트 (예: ['.qmdl', '.hdf'])
            
        Returns:
            list: 파일 경로 리스트
        """
        files = []
        
        try:
            items = []
            self.ftp.cwd(path)
            self.ftp.retrlines('LIST', items.append)
            
            for item in items:
                parts = item.split()
                if len(parts) < 9:
                    continue
                
                permissions = parts[0]
                name = ' '.join(parts[8:])
                
                # . 과 .. 제외
                if name in ['.', '..']:
                    continue
                
                # 파일만 처리 (디렉토리 제외)
                if not permissions.startswith('d'):
                    if extensions:
                        ext = os.path.splitext(name)[1].lower()
                        if ext in extensions:
                            full_path = os.path.join(path, name).replace('\\', '/')
                            files.append(full_path)
                    else:
                        full_path = os.path.join(path, name).replace('\\', '/')
                        files.append(full_path)
            
        except Exception as e:
            print(f"파일 목록 오류 ({path}): {str(e)}")
        
        return files
    
    def file_exists(self, filepath):
        """
        FTP 서버에 파일이 존재하는지 확인
        
        Args:
            filepath: 확인할 파일 경로
            
        Returns:
            bool: 파일 존재 여부
        """
        try:
            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            
            if directory:
                self.ftp.cwd(directory)
            
            files = self.ftp.nlst()
            return filename in files
        except:
            return False
    
    def download_file(self, remote_path, local_path):
        """
        FTP 서버에서 파일 다운로드
        
        Args:
            remote_path: FTP 서버의 파일 경로
            local_path: 로컬 저장 경로
            
        Returns:
            tuple: (성공 여부, 메시지)
        """
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote_path}', f.write)
            
            return True, f"다운로드 완료: {remote_path}"
        except Exception as e:
            return False, f"다운로드 실패: {str(e)}"
    
    def upload_file(self, local_path, remote_path):
        """
        FTP 서버로 파일 업로드
        
        Args:
            local_path: 로컬 파일 경로
            remote_path: FTP 서버의 저장 경로
            
        Returns:
            tuple: (성공 여부, 메시지)
        """
        try:
            # 디렉토리 생성 (필요시)
            directory = os.path.dirname(remote_path)
            if directory:
                self._create_remote_directory(directory)
            
            with open(local_path, 'rb') as f:
                self.ftp.storbinary(f'STOR {remote_path}', f)
            
            return True, f"업로드 완료: {remote_path}"
        except Exception as e:
            return False, f"업로드 실패: {str(e)}"
    
    def _create_remote_directory(self, path):
        """
        FTP 서버에 디렉토리 생성 (재귀적)
        
        Args:
            path: 생성할 디렉토리 경로
        """
        parts = path.split('/')
        current = ''
        
        for part in parts:
            if not part:
                continue
            
            current = f"{current}/{part}" if current else part
            
            try:
                self.ftp.cwd(current)
            except:
                try:
                    self.ftp.mkd(current)
                    self.ftp.cwd(current)
                except:
                    pass
        
        # 루트로 돌아가기
        self.ftp.cwd('/')
