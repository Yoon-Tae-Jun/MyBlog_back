import os
import shutil
import subprocess
from datetime import datetime
import json

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))         # /MyBlog/back
FRONT_DIR = os.path.join(ROOT_DIR, "..", "front")             # /MyBlog/front
PUBLIC_DB_PATH = os.path.join(FRONT_DIR, "public", "db.json")
SOURCE_DB_PATH = os.path.join(ROOT_DIR, "db.json")

print("1. Notion 데이터 최신화 및 이미지 다운로드 중...")
try:
    # 파이썬 가상환경 경로를 통해 main.py 실행
    venv_python = os.path.join(ROOT_DIR, "back", "bin", "python3")
    if os.path.exists(venv_python):
        subprocess.run([venv_python, os.path.join(ROOT_DIR, "main.py")], check=True)
    else:
        subprocess.run(["python3", os.path.join(ROOT_DIR, "main.py")], check=True)
except Exception as e:
    print(f"파이썬 실행 중 오류가 발생했습니다: {e}")

shutil.copyfile(SOURCE_DB_PATH, PUBLIC_DB_PATH)
print(f"{SOURCE_DB_PATH} → {PUBLIC_DB_PATH} 복사 완료")

os.chdir(FRONT_DIR)

# 새롭게 생성된 page_img 내부의 이미지와 db.json을 모두 추적하도록 public 전체를 추가합니다.
subprocess.run(["git", "add", "public"])
subprocess.run(["git", "commit", "-m", f"Update db.json ({datetime.now().isoformat()})"], check=False)
subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
print("Git push 완료")

subprocess.run(["npm", "run", "build"], check=True)
print("Build 완료")

subprocess.run(["npm", "run", "deploy"], check=True)
print("GitHub Pages 배포 완료")