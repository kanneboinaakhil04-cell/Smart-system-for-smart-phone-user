import os
import json
import asyncio
from typing import Dict, Any, List, Optional
import uuid
import re
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "phonebalance")

class JSONCollection:
    def __init__(self, name: str, parent_store: "JSONMongoStore"):
        self.name = name
        self.store = parent_store

    def _get_data(self) -> List[Dict[str, Any]]:
        return self.store.data.get(self.name, [])

    def _save_data(self, data: List[Dict[str, Any]]):
        self.store.data[self.name] = data
        self.store._persist()

    async def insert_one(self, document: Dict[str, Any]):
        doc_copy = dict(document)
        if "_id" not in doc_copy:
            doc_copy["_id"] = str(uuid.uuid4())
        if "created_at" not in doc_copy and "timestamp" not in doc_copy:
            doc_copy["created_at"] = datetime.utcnow().isoformat()
        
        data = self._get_data()
        data.append(doc_copy)
        self._save_data(data)
        
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return InsertResult(doc_copy["_id"])

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = self._get_data()
        for doc in data:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return dict(doc)
        return None

    def find(self, query: Optional[Dict[str, Any]] = None):
        data = self._get_data()
        results = []
        query = query or {}
        for doc in data:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(dict(doc))
        
        class Cursor:
            def __init__(self, items):
                self.items = items
            
            def sort(self, key_or_list, direction=1):
                if isinstance(key_or_list, str):
                    key = key_or_list
                    rev = direction == -1
                elif isinstance(key_or_list, list):
                    key = key_or_list[0][0]
                    rev = key_or_list[0][1] == -1
                else:
                    key = "_id"
                    rev = False
                
                self.items = sorted(self.items, key=lambda x: x.get(key, ""), reverse=rev)
                return self

            def limit(self, l: int):
                self.items = self.items[:l]
                return self

            async def to_list(self, length: Optional[int] = None):
                if length is not None:
                    return self.items[:length]
                return self.items

            def __aiter__(self):
                self._iter = iter(self.items)
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        return Cursor(results)

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        data = self._get_data()
        modified_count = 0
        set_fields = update.get("$set", {})
        inc_fields = update.get("$inc", {})
        
        target_idx = -1
        for idx, doc in enumerate(data):
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                target_idx = idx
                break
        
        if target_idx >= 0:
            doc = data[target_idx]
            for k, v in set_fields.items():
                doc[k] = v
            for k, v in inc_fields.items():
                doc[k] = doc.get(k, 0) + v
            data[target_idx] = doc
            modified_count = 1
            self._save_data(data)
        elif upsert:
            new_doc = dict(query)
            for k, v in set_fields.items():
                new_doc[k] = v
            for k, v in inc_fields.items():
                new_doc[k] = v
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4())
            data.append(new_doc)
            self._save_data(data)
            modified_count = 1

        class UpdateResult:
            def __init__(self, count):
                self.modified_count = count
        return UpdateResult(modified_count)

    async def delete_one(self, query: Dict[str, Any]):
        data = self._get_data()
        initial_len = len(data)
        new_data = []
        deleted = False
        for doc in data:
            if not deleted:
                match = True
                for k, v in query.items():
                    if doc.get(k) != v:
                        match = False
                        break
                if match:
                    deleted = True
                    continue
            new_data.append(doc)
        
        self._save_data(new_data)
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
        return DeleteResult(initial_len - len(new_data))

    async def count_documents(self, query: Dict[str, Any]) -> int:
        data = self._get_data()
        count = 0
        for doc in data:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count


class JSONMongoStore:
    def __init__(self, filepath: str = "data/db.json"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {}

    def _persist(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_collection(self, name: str) -> JSONCollection:
        return JSONCollection(name, self)

    def __getitem__(self, name: str) -> JSONCollection:
        return self.get_collection(name)


class DatabaseWrapper:
    def __init__(self):
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.mongo_db = None
        self.json_store = JSONMongoStore()
        self.using_mongodb = False

    async def init_db(self):
        try:
            client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2000)
            await client.admin.command('ping')
            self.mongo_client = client
            self.mongo_db = client[DB_NAME]
            self.using_mongodb = True
            print(f"[Database] Successfully connected to MongoDB database '{DB_NAME}' at {MONGODB_URL}")
        except Exception as e:
            self.using_mongodb = False
            print(f"[Database] MongoDB not available ({e}). Using embedded JSON database store.")

    def get_collection(self, name: str):
        if self.using_mongodb and self.mongo_db is not None:
            return self.mongo_db[name]
        return self.json_store[name]

    def __getitem__(self, name: str):
        return self.get_collection(name)

db_wrapper = DatabaseWrapper()

def get_db():
    return db_wrapper
