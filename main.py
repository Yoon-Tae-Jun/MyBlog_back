import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class NotionLoader():
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.headers = {
            "Authorization": "Bearer " + self.token,
            "Notion-Version": "2022-02-22"
        }
        self.loadMetaData()

    def loadMetaData(self):
        with open("metadata.json", "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        print("메타 데이터 불러오기 완료")

    def WriteDbData(self, data):
        with open('db.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("DB 파일 저장 완료")

    # =======================
    #      Database 부분
    # =======================
    def readDatabase(self, databaseId, headers):
        readUrl = f"https://api.notion.com/v1/databases/{databaseId}/query"
        res = requests.post(readUrl, headers=headers)
        print("DB 상태코드: " + str(res.status_code))
        data = res.json()
        return data

    def parseData(self, data, attr):
        """metadata.json의 attribute 목록 기준으로 DB row 파싱"""
        parse_data = {}
        for idx, result in enumerate(data["results"]):
            row_data = {}
            for p in attr:
                r_type = result["properties"][p]["type"]
                prop = result["properties"][p][r_type]

                if r_type == "select":
                    row_data[p] = prop["name"]
                elif r_type == "multi_select":
                    row_data[p] = [s["name"] for s in prop]
                elif r_type == "files":
                    if prop:
                        row_data[p] = prop[0]["name"]
                    else:
                        row_data[p] = None
                else:
                    # title / rich_text 등 텍스트 계열
                    if prop:
                        row_data[p] = prop[0].get("plain_text", "")
                    else:
                        row_data[p] = ""
            parse_data[idx] = row_data
        return parse_data

    # =======================
    #     Block / Page 부분
    # =======================
    def get_block_children(self, block_id: str):
        """block_id(page_id 포함)의 직계 children을 전부 가져옴 (pagination 처리)"""
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"
        all_results = []
        cursor = None

        while True:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor

            res = requests.get(url, headers=self.headers, params=params)
            if res.status_code != 200:
                print("children 상태코드:", res.status_code, res.text)
                break

            data = res.json()
            all_results.extend(data.get("results", []))

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")

        return all_results

    def _simplify_rich_text(self, rich_text_list):
        """bold/italic/underline, color, 링크까지 유지"""
        simple = []
        for t in rich_text_list:
            simple.append({
                "plain_text": t.get("plain_text", ""),
                "href": t.get("href"),
                "annotations": t.get("annotations", {})
            })
        return simple

    def _simplify_block_recursive(self, block: dict):
        """Notion block 하나를 React 렌더링용으로 정리 + children 재귀 포함"""
        btype = block["type"]

        simple = {
            "id": block["id"],
            "type": btype,
            "has_children": bool(block.get("has_children", False))
        }

        # ---- 텍스트 계열 블록 ----
        if btype in (
            "paragraph",
            "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item",
            "to_do", "toggle",
            "quote", "callout"
        ):
            node = block[btype]

            simple[btype] = {
                "rich_text": self._simplify_rich_text(node.get("rich_text", [])),
                "color": node.get("color", "default"),
            }

            if btype == "to_do":
                simple[btype]["checked"] = node.get("checked", False)

            if btype == "callout":
                simple[btype]["icon"] = node.get("icon")

        # ---- 코드 블록 ----
        elif btype == "code":
            node = block["code"]
            simple["code"] = {
                "rich_text": self._simplify_rich_text(node.get("rich_text", [])),
                "language": node.get("language", None)
            }

        # ---- 이미지 ----
        elif btype == "image":
            img = block["image"]
            img_type = img.get("type")

            if img_type == "file":
                url = img["file"]["url"]
            else:  # external
                url = img["external"]["url"]

            # presigned URL 맨 끝에서 파일 이름만 추출
            # 예: .../내사진.jpg?X-Amz-...  ->  "내사진.jpg"
            last_part = url.split("/")[-1]
            filename = last_part.split("?")[0]

            simple["image"] = {
                "name": filename,          # ✅ JSON에는 파일 이름만 저장
                "source_type": img_type,
                "caption": self._simplify_rich_text(img.get("caption", []))
            }

        # ---- 구분선 ----
        elif btype == "divider":
            simple["divider"] = True

        # ---- 북마크, 링크 embed 등 ----
        elif btype == "bookmark":
            simple["bookmark"] = {
                "url": block["bookmark"].get("url")
            }

        elif btype == "embed":
            simple["embed"] = {
                "url": block["embed"].get("url")
            }

        # ---- 컬럼 레이아웃 ----
        elif btype == "column_list":
            # 실제 children(column 들)은 children 재귀에서 처리
            pass

        elif btype == "column":
            # column 자체는 레이아웃 역할만
            pass

        # 기타 타입들 (간단하게 raw 보존)
        else:
            simple["raw"] = {btype: block.get(btype, {})}

        # ---- children 재귀 ----
        if simple["has_children"]:
            children_raw = self.get_block_children(block["id"])
            simple["children"] = [
                self._simplify_block_recursive(child)
                for child in children_raw
            ]

        return simple

    def build_page_json(self, page_id: str):
        """주어진 page_id의 전체 블록 트리를 React 렌더링용 JSON(list)으로 생성"""
        root_blocks = self.get_block_children(page_id)
        simplified = [
            self._simplify_block_recursive(b)
            for b in root_blocks
        ]
        return simplified

    # =======================
    #      통합 저장 부분
    # =======================
    def saveDbFile(self):
        parse_data = {}

        # 1) DB 섹션 처리
        for name, info in self.metadata["database"].items():
            try:
                d = self.readDatabase(info["db_id"], self.headers)
                parse_data[name] = self.parseData(d, info["attribute"])
            except Exception as e:
                print(f"[경고] DB '{name}' 로드 중 오류 발생: {e}")
                parse_data[name] = {}

        # 2) 여러 페이지 지원 (전체 페이지 loop)
        if "page" in self.metadata:
            for page_name, page_info in self.metadata["page"].items():
                page_id = page_info["page_id"]
                try:
                    blocks = self.build_page_json(page_id)
                    parse_data[page_name] = {idx: b for idx, b in enumerate(blocks)}
                except Exception as e:
                    print(f"[경고] 페이지 '{page_name}' 로드 중 오류 발생: {e}")
                    parse_data[page_name] = {}

        # 3) 저장
        self.WriteDbData(parse_data)


# ===== 실행 =====
if __name__ == "__main__":
    d = NotionLoader()
    d.saveDbFile()
