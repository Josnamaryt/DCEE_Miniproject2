from datetime import datetime
from bson import ObjectId
from app import mongo

# Create quiz table/collection
quiz_collection = mongo.db.quizzes

# Create indexes for better query performance
quiz_collection.create_index([("course_id", 1)])
quiz_collection.create_index([("instructor_id", 1)])
quiz_collection.create_index([("created_at", -1)])

# Sample quiz document structure
"""
{
    "_id": ObjectId,
    "title": str,
    "description": str,
    "course_id": ObjectId,
    "course_name": str,
    "instructor_id": str,
    "instructor_name": str,
    "questions": [
        {
            "question": str,
            "options": [str, str, str, str],
            "correct_answer": int
        }
    ],
    "created_at": datetime
}
""" 