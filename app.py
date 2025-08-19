from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
import pyodbc
from tmdb_client import get_movies_by_genres_and_keywords, get_movie_details
from llm_analyzer import analyze_user_input
import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from tmdb_client import get_watch_providers
from collections import defaultdict
import os

load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

app = Flask(__name__)
app.secret_key = "moodflix_secret_key"
bcrypt = Bcrypt(app)

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=MoodFlixDB;'
        'Trusted_Connection=yes;'
    )
def analyze_user_history(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT RecommendedMovie, QuestionText
        FROM Recommendations
        WHERE UserId = ?
        ORDER BY Timestamp DESC
        """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # En çok geçen kelimeleri ve türleri basitçe analiz et
    all_questions = " ".join(row.QuestionText for row in rows)
    return analyze_user_input(all_questions)


def send_reset_code(email, code):
    msg = MIMEText(f"\u015eifre s\u0131f\u0131rlama kodunuz: {code}")
    msg["Subject"] = "MoodFlix \u015eifre S\u0131f\u0131rlama"
    msg["From"] = EMAIL_USER
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("✅ Kod g\u00f6nderildi:", code)
    except Exception as e:
        print("❌ Mail g\u00f6nderilemedi:", e)

        

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("recommend"))  # Artık index.html yerine direkt öneri sayfası

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Users (Username, Email, PasswordHash) VALUES (?, ?, ?)",
                           (username, email, password_hash))
            conn.commit()
            flash("K\u0131yat ba\u015far\u0131l\u0131!", "success")
            return redirect(url_for("login"))
        except:
            flash("Kullan\u0131c\u0131 ad\u0131 veya e-posta zaten var!", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id, PasswordHash FROM Users WHERE Username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user.PasswordHash, password):
            session["user_id"] = user.Id
            session["username"] = username
            return redirect(url_for("index"))
        else:
            flash("Kullan\u0131c\u0131 ad\u0131 veya \u015fifre hatal\u0131!", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("\u00c7\u0131k\u0131\u015f yap\u0131ld\u0131.", "info")
    return redirect(url_for("login"))

@app.route("/recommend", methods=["GET", "POST"])
def recommend():
    if "user_id" not in session:
        return redirect(url_for("login"))

    movies = []
    error = None

    if request.method == "POST":
        user_input = request.form.get("user_input")

        try:
            if user_input:
                result = analyze_user_input(user_input)
            else:
                result = analyze_user_history(session["user_id"])  # Özel öneri geçmişten

            if result:
                genres = result.get("turler", [])
                keywords = result.get("anahtar_kelimeler", [])

                if not genres:
                    error = "🎬 Ruh haline göre film bulamadık. Lütfen bir şeyler yaz."
                else:
                    movies = get_movies_by_genres_and_keywords(genres, keywords)
                    if not movies:
                        error = "🎭 Üzgünüz, bu duyguya uygun film bulunamadı."
                    else:
                        # Sadece kullanıcı bir şey yazdıysa veritabanına kaydet
                        if user_input:
                            conn = get_connection()
                            cursor = conn.cursor()
                            for movie in movies:
                                cursor.execute("""
                                    INSERT INTO Recommendations (UserId, QuestionText, RecommendedMovie, RecommendedMovieId)
                                    VALUES (?, ?, ?, ?)
                                """, (
                                    session["user_id"],
                                    user_input,
                                    movie["title"],
                                    movie["id"]
                                ))
                            conn.commit()
                            conn.close()
            else:
                error = "Henüz seninle ilgili öneri geçmişimiz yok. Ruh halini yazıp başlayabilirsin 🎬"

        except Exception as e:
            print("❌ Hata:", e)
            error = "⚠️ Sistem, yazdıklarını anlayamadı. Lütfen ruh halinle ilgili bir şeyler yaz (örneğin: 'Yorgunum ve hüzünlüyüm')."

    # Önerileri ayır: 1 tanesi en popüler (en üstte gösterilecek)
    if movies:
        top_movie = max(movies, key=lambda x: x["vote_average"])
        other_movies = [m for m in movies if m["id"] != top_movie["id"]]
    else:
        top_movie = None
        other_movies = []

    return render_template("recommend.html", top_movie=top_movie, other_movies=other_movies, error=error)

@app.route("/movie/<int:movie_id>", methods=["GET", "POST"])
def movie_detail(movie_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    movie = get_movie_details(movie_id)
    if not movie:
        flash("Film bulunamad\u0131!", "danger")
        return redirect(url_for("recommend"))
    
    # Film detaylarını al
        movie = get_movie_details(movie_id)
        platforms = get_watch_providers(movie_id)  # ✅ platformları çek

    if request.method == "POST":
        comment_text = request.form.get("comment_text")
        if comment_text:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Comments (UserId, MovieId, CommentText) VALUES (?, ?, ?)",
                           (session["user_id"], movie_id, comment_text))
            conn.commit()
            conn.close()
            flash("Yorum eklendi.", "success")
            return redirect(url_for("movie_detail", movie_id=movie_id))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Users.Username, Comments.CommentText, Comments.CreatedAt FROM Comments JOIN Users ON Comments.UserId = Users.Id WHERE MovieId = ? ORDER BY CreatedAt DESC", (movie_id,))
    rows = cursor.fetchall()
    comments = [{"username": row.Username, "comment_text": row.CommentText, "created_at": row.CreatedAt.strftime("%d.%m.%Y %H:%M")} for row in rows]

    cursor.execute("SELECT 1 FROM Favorites WHERE UserId = ? AND MovieId = ?", (session["user_id"], movie_id))
    is_favorite = cursor.fetchone() is not None
    conn.close()

    return render_template("movie_detail.html", movie=movie, comments=comments, is_favorite=is_favorite)

@app.route("/favorite/<int:movie_id>", methods=["POST"])
def add_favorite(movie_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Favorites WHERE UserId = ? AND MovieId = ?", (session["user_id"], movie_id))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute("INSERT INTO Favorites (UserId, MovieId) VALUES (?, ?)", (session["user_id"], movie_id))
        conn.commit()
        flash("Favorilere eklendi!", "success")
    else:
        flash("Bu film zaten favorilerinde.", "info")
    conn.close()
    return redirect(request.referrer or url_for("recommend"))

@app.route("/favorites")
def favorites():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MovieId FROM Favorites WHERE UserId = ?", (session["user_id"],))
    favorite_ids = [row.MovieId for row in cursor.fetchall()]
    conn.close()

    favorite_movies = [get_movie_details(movie_id) for movie_id in favorite_ids]
    return render_template("favorites.html", movies=favorite_movies)

@app.route("/remove_favorite/<int:movie_id>", methods=["POST"])
def remove_favorite(movie_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Favorites WHERE UserId = ? AND MovieId = ?", (session["user_id"], movie_id))
    conn.commit()
    conn.close()
    flash("Favorilerden kald\u0131r\u0131ld\u0131.", "success")
    return redirect(url_for("favorites"))

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT QuestionText, RecommendedMovie, RecommendedMovieId, Timestamp
        FROM Recommendations
        WHERE UserId = ?
        ORDER BY Timestamp DESC
    """, (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    grouped_data = defaultdict(list)
    for row in rows:
        question = row[0]
        movie = {
            "title": row[1],
            "id": row[2],
            "timestamp": row[3]
        }
        grouped_data[question].append(movie)

    return render_template("history.html", grouped_data=grouped_data)
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        step = request.form.get("step")

        if step == "send_code":
            email = request.form["email"]
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT Id FROM Users WHERE Email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if user:
                code = str(random.randint(100000, 999999))
                session["reset_email"] = email
                session["reset_code"] = code
                session["step"] = "awaiting_code"
                send_reset_code(email, code)
                flash("Do\u011frulama kodu e-postana g\u00f6nderildi.", "info")
            else:
                flash("Bu e-posta ile kay\u0131tl\u0131 kullan\u0131c\u0131 bulunamad\u0131.", "danger")

        elif step == "verify_code":
            input_code = request.form["code"]
            if input_code == session.get("reset_code"):
                session["step"] = "awaiting_password"
                flash("Kod do\u011fruland\u0131. L\u00fctfen yeni \u015fifreni gir.", "info")
            else:
                flash("Kod yanl\u0131\u015f!", "danger")

        elif step == "reset_password":
            new_password = request.form["new_password"]
            password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET PasswordHash = ? WHERE Email = ?", (password_hash, session["reset_email"]))
            conn.commit()
            conn.close()
            session.pop("reset_email", None)
            session.pop("reset_code", None)
            session.pop("step", None)
            flash("\u015eifre ba\u015far\u0131yla g\u00fcncellendi. Giris yapabilirsin.", "success")
            return redirect(url_for("login"))

    return render_template("forgot_password.html")

if __name__ == "__main__":
    print("🚀 Flask çalıştırılıyor...")
    app.run(debug=True)
