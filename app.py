"""
Naebak Content Service - Flask Application

This is the main application file for the Naebak Content Service. It provides a RESTful API
for managing static content pages and dynamic articles. The service supports full CRUD operations
for both content types and is designed to serve content to the main Naebak platform.

The service manages two main types of content:
1. ContentPage: Static pages like "About Us", "Terms of Service", etc.
2. Article: Dynamic content like blog posts, news articles, and announcements.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging
from config import get_config
from models import db, ContentPage, Article

# Setup application
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Setup CORS
CORS(app, origins=app.config["CORS_ALLOWED_ORIGINS"])

# Setup database
db.init_app(app)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create tables when the application starts for the first time
with app.app_context():
    db.create_all()

@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for service monitoring.
    
    This endpoint is used by load balancers and monitoring systems to verify
    that the service is running and can connect to the database.
    
    Returns:
        JSON response with service status and database connectivity information.
    """
    try:
        # Try to connect to the database to verify its health
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok", "service": "naebak-content-service", "version": "1.0.0"}), 200
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({"status": "error", "service": "naebak-content-service", "error": "Database connection failed"}), 500

# --- ContentPage Endpoints ---
@app.route("/api/content/pages", methods=["POST"])
def create_content_page():
    """
    Create a new static content page.
    
    This endpoint creates a new ContentPage with the provided slug, title, and content.
    The slug must be unique across all content pages and should be URL-friendly.
    
    Request Body:
        slug (str): Unique identifier for the page (URL-friendly).
        title (str): Display title of the page.
        content (str): Main content of the page (HTML or markdown).
    
    Returns:
        JSON response with success message and the created page ID, or error details.
    """
    data = request.get_json()
    if not data or not all(key in data for key in ["slug", "title", "content"]):
        return jsonify({"error": "Missing required fields: slug, title, content"}), 400
    
    # Check if a page with this slug already exists
    if ContentPage.query.filter_by(slug=data["slug"]).first():
        return jsonify({"error": "Page with this slug already exists"}), 409

    new_page = ContentPage(slug=data["slug"], title=data["title"], content=data["content"])
    db.session.add(new_page)
    db.session.commit()
    
    logger.info(f"Created new content page with slug: {data['slug']}")
    return jsonify({"message": "Content page created", "id": new_page.id}), 201

@app.route("/api/content/pages", methods=["GET"])
def get_content_pages():
    """
    Retrieve all static content pages.
    
    This endpoint returns a list of all content pages in the system.
    It's typically used for administrative interfaces or site navigation.
    
    Returns:
        JSON response with an array of all content pages.
    """
    pages = ContentPage.query.all()
    pages_data = [page.to_dict() for page in pages]
    
    logger.info(f"Retrieved {len(pages_data)} content pages")
    return jsonify(pages_data), 200

@app.route("/api/content/pages/<slug>", methods=["GET"])
def get_content_page(slug):
    """
    Retrieve a specific content page by its slug.
    
    This endpoint returns the details of a single content page identified by its slug.
    It's the primary endpoint used by the frontend to display static pages.
    
    Args:
        slug (str): The unique slug identifier of the content page.
    
    Returns:
        JSON response with the content page details, or 404 if not found.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    
    logger.info(f"Retrieved content page: {slug}")
    return jsonify(page.to_dict()), 200

@app.route("/api/content/pages/<slug>", methods=["PUT"])
def update_content_page(slug):
    """
    Update an existing content page.
    
    This endpoint allows updating the title and/or content of an existing page.
    The last_updated timestamp is automatically updated when changes are made.
    
    Args:
        slug (str): The unique slug identifier of the content page to update.
    
    Request Body:
        title (str, optional): New title for the page.
        content (str, optional): New content for the page.
    
    Returns:
        JSON response with success message and page ID, or error details.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update the page using the model method
    page.update_content(
        title=data.get("title"),
        content=data.get("content")
    )
    db.session.commit()
    
    logger.info(f"Updated content page: {slug}")
    return jsonify({"message": "Content page updated", "id": page.id}), 200

@app.route("/api/content/pages/<slug>", methods=["DELETE"])
def delete_content_page(slug):
    """
    Delete a content page.
    
    This endpoint permanently removes a content page from the system.
    Use with caution as this operation cannot be undone.
    
    Args:
        slug (str): The unique slug identifier of the content page to delete.
    
    Returns:
        JSON response with success message, or 404 if page not found.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    db.session.delete(page)
    db.session.commit()
    
    logger.info(f"Deleted content page: {slug}")
    return jsonify({"message": "Content page deleted"}), 204

# --- Article Endpoints ---
@app.route("/api/content/articles", methods=["POST"])
def create_article():
    """
    Create a new article.
    
    This endpoint creates a new Article with the provided title, content, and optional author.
    The publish_date is automatically set to the current timestamp.
    
    Request Body:
        title (str): Title of the article.
        content (str): Main content of the article (HTML or markdown).
        author (str, optional): Name of the article author.
    
    Returns:
        JSON response with success message and the created article ID, or error details.
    """
    data = request.get_json()
    if not data or not all(key in data for key in ["title", "content"]):
        return jsonify({"error": "Missing required fields: title, content"}), 400

    new_article = Article(title=data["title"], content=data["content"], author=data.get("author"))
    db.session.add(new_article)
    db.session.commit()
    
    logger.info(f"Created new article: {data['title']}")
    return jsonify({"message": "Article created", "id": new_article.id}), 201

@app.route("/api/content/articles", methods=["GET"])
def get_articles():
    """
    Retrieve all articles.
    
    This endpoint returns a list of all articles in the system, ordered by
    publication date (newest first). It supports query parameters for filtering.
    
    Query Parameters:
        limit (int, optional): Maximum number of articles to return.
        author (str, optional): Filter articles by author name.
    
    Returns:
        JSON response with an array of articles.
    """
    limit = request.args.get('limit', type=int)
    author = request.args.get('author')
    
    if author:
        articles = Article.get_articles_by_author(author)
    elif limit:
        articles = Article.get_recent_articles(limit)
    else:
        articles = Article.query.order_by(Article.publish_date.desc()).all()
    
    articles_data = [article.to_dict() for article in articles]
    
    logger.info(f"Retrieved {len(articles_data)} articles")
    return jsonify(articles_data), 200

@app.route("/api/content/articles/<int:article_id>", methods=["GET"])
def get_article(article_id):
    """
    Retrieve a specific article by its ID.
    
    This endpoint returns the details of a single article identified by its ID.
    It's used by the frontend to display individual article pages.
    
    Args:
        article_id (int): The unique ID of the article.
    
    Returns:
        JSON response with the article details, or 404 if not found.
    """
    article = Article.query.get_or_404(article_id)
    
    logger.info(f"Retrieved article: {article.title}")
    return jsonify(article.to_dict()), 200

@app.route("/api/content/articles/<int:article_id>", methods=["PUT"])
def update_article(article_id):
    """
    Update an existing article.
    
    This endpoint allows updating the title, content, and/or author of an existing article.
    The publish_date remains unchanged to preserve chronological ordering.
    
    Args:
        article_id (int): The unique ID of the article to update.
    
    Request Body:
        title (str, optional): New title for the article.
        content (str, optional): New content for the article.
        author (str, optional): New author for the article.
    
    Returns:
        JSON response with success message and article ID, or error details.
    """
    article = Article.query.get_or_404(article_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update the article using the model method
    article.update_article(
        title=data.get("title"),
        content=data.get("content"),
        author=data.get("author")
    )
    db.session.commit()
    
    logger.info(f"Updated article: {article.title}")
    return jsonify({"message": "Article updated", "id": article.id}), 200

@app.route("/api/content/articles/<int:article_id>", methods=["DELETE"])
def delete_article(article_id):
    """
    Delete an article.
    
    This endpoint permanently removes an article from the system.
    Use with caution as this operation cannot be undone.
    
    Args:
        article_id (int): The unique ID of the article to delete.
    
    Returns:
        JSON response with success message, or 404 if article not found.
    """
    article = Article.query.get_or_404(article_id)
    article_title = article.title  # Store for logging before deletion
    db.session.delete(article)
    db.session.commit()
    
    logger.info(f"Deleted article: {article_title}")
    return jsonify({"message": "Article deleted"}), 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
