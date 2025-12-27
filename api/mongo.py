import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGODB_URI")  # your mongodb+srv://...
DB_NAME = "nex-ai"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

company_collection = db["groq_chatbot"]["company-details"]
