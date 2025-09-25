from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging
from config import get_config
from models import db, ContentPage, Article

# إعداد التطبيق
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# إعداد CORS
CORS(app, origins=app.config["CORS_ALLOWED_ORIGINS"])

# إعداد قاعدة البيانات
db.init_app(app)

# إعداد Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# إنشاء الجداول عند بدء التطبيق لأول مرة
with app.app_context():
    db.create_all()

@app.route("/health", methods=["GET"])
def health_check():
    """فحص صحة الخدمة"""
    try:
        # محاولة الاتصال بقاعدة البيانات للتحقق من صحتها
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok", "service": "naebak-content-service", "version": "1.0.0"}), 200
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({"status": "error", "service": "naebak-content-service", "error": "Database connection failed"}), 500

# --- ContentPage Endpoints ---
@app.route("/api/content/pages", methods=["POST"])
def create_content_page():
    data = request.get_json()
    if not data or not all(key in data for key in ["slug", "title", "content"]):
        return jsonify({"error": "Missing data"}), 400
    
    if ContentPage.query.filter_by(slug=data["slug"]).first():
        return jsonify({"error": "Page with this slug already exists"}), 409

    new_page = ContentPage(slug=data["slug"], title=data["title"], content=data["content"])
    db.session.add(new_page)
    db.session.commit()
    return jsonify({"message": "Content page created", "id": new_page.id}), 201

@app.route("/api/content/pages", methods=["GET"])
def get_content_pages():
    pages = ContentPage.query.all()
    return jsonify([{"id": page.id, "slug": page.slug, "title": page.title, "content": page.content, "last_updated": page.last_updated.isoformat()} for page in pages]), 200

@app.route("/api/content/pages/<slug>", methods=["GET"])
def get_content_page(slug):
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    return jsonify({"id": page.id, "slug": page.slug, "title": page.title, "content": page.content, "last_updated": page.last_updated.isoformat()}), 200

@app.route("/api/content/pages/<slug>", methods=["PUT"])
def update_content_page(slug):
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    page.title = data.get("title", page.title)
    page.content = data.get("content", page.content)
    db.session.commit()
    return jsonify({"message": "Content page updated", "id": page.id}), 200

@app.route("/api/content/pages/<slug>", methods=["DELETE"])
def delete_content_page(slug):
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    db.session.delete(page)
    db.session.commit()
    return jsonify({"message": "Content page deleted"}), 204

# --- Article Endpoints ---
@app.route("/api/content/articles", methods=["POST"])
def create_article():
    data = request.get_json()
    if not data or not all(key in data for key in ["title", "content"]):
        return jsonify({"error": "Missing data"}), 400

    new_article = Article(title=data["title"], content=data["content"], author=data.get("author"))
    db.session.add(new_article)
    db.session.commit()
    return jsonify({"message": "Article created", "id": new_article.id}), 201

@app.route("/api/content/articles", methods=["GET"])
def get_articles():
    articles = Article.query.all()
    return jsonify([{"id": article.id, "title": article.title, "content": article.content, "author": article.author, "publish_date": article.publish_date.isoformat()} for article in articles]), 200

@app.route("/api/content/articles/<int:article_id>", methods=["GET"])
def get_article(article_id):
    article = Article.query.get_or_404(article_id)
    return jsonify({"id": article.id, "title": article.title, "content": article.content, "author": article.author, "publish_date": article.publish_date.isoformat()}), 200

@app.route("/api/content/articles/<int:article_id>", methods=["PUT"])
def update_article(article_id):
    article = Article.query.get_or_404(article_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    article.title = data.get("title", article.title)
    article.content = data.get("content", article.content)
    article.author = data.get("author", article.author)
    db.session.commit()
    return jsonify({"message": "Article updated", "id": article.id}), 200

@app.route("/api/content/articles/<int:article_id>", methods=["DELETE"])
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    return jsonify({"message": "Article deleted"}), 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)

