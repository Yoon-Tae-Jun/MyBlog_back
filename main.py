import requests
import json
from datetime import datetime
import os
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

    def readDatabase(self, databaseId, headers):
        readUrl = f"https://api.notion.com/v1/databases/{databaseId}/query"
        res = requests.post(readUrl, headers=headers)
        print("상태코드: " + str(res.status_code))
        data = res.json()
        return data

    def parseData(self, name, data, attr):
        parse_data = {}
        for idx, result in enumerate(data["results"]):
            row_data = {}
            for p in attr:
                r_type = result["properties"][p]["type"]
                if r_type == "select":
                    row_data[p] = result["properties"][p][r_type]["name"]
                elif r_type == "multi_select":
                    buf = []
                    for selects in result["properties"][p][r_type]:
                        buf.append(selects["name"])
                    row_data[p] = buf
                elif r_type == "files":
                    row_data[p] = result["properties"][p][r_type][0]["name"]
                else:
                    row_data[p] = result["properties"][p][r_type][0]["plain_text"]
                parse_data[idx] = row_data
        return parse_data

    def saveDbFile(self):
        parse_data = {}
        for name, info in self.metadata["database"].items():
            d = self.readDatabase(info["db_id"], self.headers)
            parse_data[name] = self.parseData(name, d, info["attribute"])
        self.WriteDbData(parse_data)
        

d = NotionLoader()
d.saveDbFile()