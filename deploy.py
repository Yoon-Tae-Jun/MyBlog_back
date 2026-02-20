import os
import shutil
import subprocess
from datetime import datetime
import json

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))         # /MyBlog/back
FRONT_DIR = os.path.join(ROOT_DIR, "..", "front")             # /MyBlog/front
PUBLIC_DB_PATH = os.path.join(FRONT_DIR, "public", "db.json")
SOURCE_DB_PATH = os.path.join(ROOT_DIR, "db.json")

shutil.copyfile(SOURCE_DB_PATH, PUBLIC_DB_PATH)
print(f"{SOURCE_DB_PATH} → {PUBLIC_DB_PATH} 복사 완료")

os.chdir(FRONT_DIR)

subprocess.run(["git", "add", "public/db.json"])
subprocess.run(["git", "commit", "-m", f"Update db.json ({datetime.now().isoformat()})"], check=False)
subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
print("Git push 완료")

subprocess.run(["npm", "run", "build"], check=True)
print("Build 완료")

subprocess.run(["npm", "run", "deploy"], check=True)
print("GitHub Pages 배포 완료")