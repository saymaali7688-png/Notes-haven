from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "notes.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_id INTEGER,
        FOREIGN KEY(parent_id) REFERENCES folders(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        code TEXT DEFAULT '',
        code_language TEXT DEFAULT 'cpp',
        image TEXT DEFAULT '',
        folder_id INTEGER,
        note_date TEXT,
        tags TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE SET NULL
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM folders").fetchone()[0] == 0:
        conn.execute("INSERT INTO folders (name, parent_id) VALUES (?, NULL)", ("College",))
        conn.execute("INSERT INTO folders (name, parent_id) VALUES (?, NULL)", ("Projects",))
        conn.execute("INSERT INTO folders (name, parent_id) VALUES (?, NULL)", ("Personal",))
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db()
    notes = conn.execute("""
        SELECT notes.*, folders.name AS folder_name
        FROM notes LEFT JOIN folders ON notes.folder_id = folders.id
        ORDER BY updated_at DESC
    """).fetchall()
    folders = conn.execute("SELECT * FROM folders ORDER BY name").fetchall()
    conn.close()
    return render_template("index.html", notes=notes, folders=folders)


@app.post("/api/notes")
def create_note():
    data = request.get_json(force=True)
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO notes
        (title, content, code, code_language, image, folder_id, note_date, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title", "Untitled Note"),
        data.get("content", ""),
        data.get("code", ""),
        data.get("code_language", "cpp"),
        data.get("image", ""),
        data.get("folder_id") or None,
        data.get("note_date", ""),
        data.get("tags", ""),
        now, now
    ))
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return jsonify({"success": True, "id": note_id})


@app.put("/api/notes/<int:note_id>")
def update_note(note_id):
    data = request.get_json(force=True)
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_db()
    conn.execute("""
        UPDATE notes SET
        title=?, content=?, code=?, code_language=?, image=?,
        folder_id=?, note_date=?, tags=?, updated_at=?
        WHERE id=?
    """, (
        data.get("title", "Untitled Note"),
        data.get("content", ""),
        data.get("code", ""),
        data.get("code_language", "cpp"),
        data.get("image", ""),
        data.get("folder_id") or None,
        data.get("note_date", ""),
        data.get("tags", ""),
        now,
        note_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.delete("/api/notes/<int:note_id>")
def delete_note(note_id):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.post("/api/folders")
def create_folder():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    parent_id = data.get("parent_id") or None
    if not name:
        return jsonify({"success": False, "error": "Folder name is required"}), 400
    conn = get_db()
    cur = conn.execute("INSERT INTO folders (name, parent_id) VALUES (?, ?)", (name, parent_id))
    conn.commit()
    folder_id = cur.lastrowid
    conn.close()
    return jsonify({"success": True, "id": folder_id})


@app.delete("/api/folders/<int:folder_id>")
def delete_folder(folder_id):
    conn = get_db()
    conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.post("/api/upload")
def upload_image():
    image = request.files.get("image")
    if not image or image.filename == "":
        return jsonify({"success": False, "error": "No image selected"}), 400
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    ext = os.path.splitext(image.filename)[1].lower()
    if ext not in allowed:
        return jsonify({"success": False, "error": "Unsupported image type"}), 400

    filename = datetime.now().strftime("%Y%m%d%H%M%S%f") + ext
    image.save(os.path.join(UPLOAD_DIR, filename))
    return jsonify({"success": True, "url": url_for("uploaded_file", filename=filename)})


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.get("/api/notes/<int:note_id>")
def get_note(note_id):
    conn = get_db()
    note = conn.execute("""
        SELECT notes.*, folders.name AS folder_name
        FROM notes LEFT JOIN folders ON notes.folder_id = folders.id
        WHERE notes.id=?
    """, (note_id,)).fetchone()
    conn.close()
    if not note:
        return jsonify({"error": "Note not found"}), 404
    return jsonify(dict(note))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
