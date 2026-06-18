"""
CodeCraftHub - Personalized Learning Platform API

A simple REST API for tracking development courses. Built with Flask and
JSON file storage (no database required). Supports full CRUD on courses
and has CORS enabled so a browser-based dashboard (e.g. a Bolt-generated
frontend) can call it directly.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import os

app = Flask(__name__)
CORS(app)  # Allows a browser frontend on a different origin to call this API

DATA_FILE = "courses.json"
VALID_STATUSES = {"Not Started", "In Progress", "Completed"}
REQUIRED_FIELDS = {"name", "description", "target_date", "status"}


def load_courses() -> List[Dict[str, Any]]:
    """Load all courses from the JSON file. Creates the file if missing."""
    if not os.path.exists(DATA_FILE):
        save_courses([])
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # Fail loudly rather than silently treating a corrupted file as empty
        raise RuntimeError(f"Failed to read {DATA_FILE}: {e}")


def save_courses(courses: List[Dict[str, Any]]) -> None:
    """Write the full courses list back to the JSON file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(courses, f, indent=2)
    except IOError as e:
        raise RuntimeError(f"Failed to write {DATA_FILE}: {e}")


def get_next_id(courses: List[Dict[str, Any]]) -> int:
    """Generate the next sequential ID, starting at 1."""
    if not courses:
        return 1
    return max(course["id"] for course in courses) + 1

# GET /api/courses/stats - Get basic statistics about courses
@app.route("/api/courses/stats", methods=["GET"])
def get_course_stats():
    try:
        data = load_data()
        courses = data.get("courses", [])

        total = len(courses)
        by_status = {"Not Started": 0, "In Progress": 0, "Completed": 0}

        for c in courses:
            status = c.get("status")
            if status in by_status:
                by_status[status] += 1

        return jsonify({"total": total, "by_status": by_status}), 200
    except Exception as e:
        # Simple error reporting for beginners
        return jsonify({"error": "Failed to compute stats", "detail": str(e)}), 500

def find_course(courses: List[Dict[str, Any]], course_id: int) -> Optional[Dict[str, Any]]:
    """Return the course with the given ID, or None if not found."""
    return next((c for c in courses if c["id"] == course_id), None)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


@app.route("/api/courses", methods=["POST"])
def create_course():
    """Add a new course. Requires name, description, target_date, status."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    if data["status"] not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400

    courses = load_courses()
    new_course = {
        "id": get_next_id(courses),
        "name": data["name"],
        "description": data["description"],
        "target_date": data["target_date"],
        "status": data["status"],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    courses.append(new_course)
    save_courses(courses)
    return jsonify(new_course), 201


@app.route("/api/courses", methods=["GET"])
def get_courses():
    """Return all courses."""
    return jsonify(load_courses()), 200


@app.route("/api/courses/stats", methods=["GET"])
def get_stats():
    """Return course counts: total and broken down by status.

    Defined before the <int:course_id> route so it never gets shadowed.
    """
    courses = load_courses()
    stats = {status: 0 for status in VALID_STATUSES}
    for course in courses:
        stats[course["status"]] += 1
    return jsonify({"total": len(courses), "by_status": stats}), 200


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id: int):
    """Return a single course by ID."""
    course = find_course(load_courses(), course_id)
    if course is None:
        return jsonify({"error": f"Course {course_id} not found"}), 404
    return jsonify(course), 200


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id: int):
    """Update one or more fields of an existing course (partial update)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    if "status" in data and data["status"] not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400

    courses = load_courses()
    course = find_course(courses, course_id)
    if course is None:
        return jsonify({"error": f"Course {course_id} not found"}), 404

    # Only update fields that were actually provided in the request
    for field in ("name", "description", "target_date", "status"):
        if field in data:
            course[field] = data[field]

    save_courses(courses)
    return jsonify(course), 200


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id: int):
    """Delete a course by ID."""
    courses = load_courses()
    course = find_course(courses, course_id)
    if course is None:
        return jsonify({"error": f"Course {course_id} not found"}), 404

    courses = [c for c in courses if c["id"] != course_id]
    save_courses(courses)
    return jsonify({"message": f"Course {course_id} deleted"}), 200


if __name__ == "__main__":
    print("CodeCraftHub API is starting...")
    print(f"Data will be stored in: {os.path.abspath(DATA_FILE)}")
    print("API will be available at: http://localhost:8000")
    app.run(host="localhost", port=8000, debug=True)
