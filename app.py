"""
Naebak Content Service - Enhanced Flask Application

This is the main application file for the Naebak Content Service. It provides a comprehensive
RESTful API for managing content with advanced features including:
- Content organization (categories and tags)
- Content moderation workflow
- Version control and rollback
- Media management
- Full-text search
- SEO optimization
- Content analytics

The service manages multiple content types:
1. ContentPage: Static pages like "About Us", "Terms of Service", etc.
2. Article: Dynamic content like blog posts, news articles, and announcements
3. Category: Hierarchical content organization
4. Tag: Flexible content labeling
5. Media: File and media asset management
"""

import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging
import jwt
from functools import wraps
from slugify import slugify
import magic
from PIL import Image

from config import get_config
from models import (
    db, ContentPage, Article, Category, Tag, Media, ContentVersion,
    ContentStatus, MediaType
)

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

# Authentication decorator
def token_required(f):
    """
    Decorator to require JWT authentication for protected endpoints.
    
    This decorator validates JWT tokens and extracts user information
    for use in protected endpoints.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            current_user_role = data.get('role', 'user')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user_id, current_user_role, *args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator to require admin role for administrative endpoints.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            current_user_role = data.get('role', 'user')
            
            if current_user_role not in ['admin', 'moderator']:
                return jsonify({'error': 'Admin access required'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user_id, current_user_role, *args, **kwargs)
    
    return decorated

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
        return jsonify({
            "status": "ok", 
            "service": "naebak-content-service", 
            "version": "2.0.0",
            "features": ["content_management", "moderation", "versioning", "search", "media"]
        }), 200
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({
            "status": "error", 
            "service": "naebak-content-service", 
            "error": "Database connection failed"
        }), 500

# --- Category Management Endpoints ---
@app.route("/api/content/categories", methods=["POST"])
@admin_required
def create_category(current_user_id, current_user_role):
    """
    Create a new content category.
    
    This endpoint creates a new Category for organizing content.
    Categories support hierarchical organization with parent-child relationships.
    
    Request Body:
        name (str): Display name of the category.
        description (str, optional): Description of the category.
        parent_id (int, optional): ID of parent category for hierarchy.
    
    Returns:
        JSON response with success message and the created category, or error details.
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400
    
    # Generate slug from name
    slug = slugify(data['name'])
    
    # Check if a category with this slug already exists
    if Category.query.filter_by(slug=slug).first():
        return jsonify({"error": "Category with this name already exists"}), 409
    
    # Validate parent category if provided
    parent_id = data.get('parent_id')
    if parent_id:
        parent = Category.query.get(parent_id)
        if not parent:
            return jsonify({"error": "Parent category not found"}), 404
    
    new_category = Category(
        name=data['name'],
        slug=slug,
        description=data.get('description'),
        parent_id=parent_id
    )
    
    db.session.add(new_category)
    db.session.commit()
    
    logger.info(f"Created new category: {data['name']} by user {current_user_id}")
    return jsonify({
        "message": "Category created successfully",
        "category": new_category.to_dict()
    }), 201

@app.route("/api/content/categories", methods=["GET"])
def get_categories():
    """
    Retrieve all active categories.
    
    Query Parameters:
        include_children (bool): Include child categories in response.
        parent_id (int): Filter by parent category ID.
    
    Returns:
        JSON response with an array of categories.
    """
    include_children = request.args.get('include_children', 'false').lower() == 'true'
    parent_id = request.args.get('parent_id', type=int)
    
    query = Category.query.filter_by(is_active=True)
    
    if parent_id is not None:
        query = query.filter_by(parent_id=parent_id)
    
    categories = query.order_by(Category.name).all()
    categories_data = [cat.to_dict(include_children=include_children) for cat in categories]
    
    logger.info(f"Retrieved {len(categories_data)} categories")
    return jsonify(categories_data), 200

@app.route("/api/content/categories/<int:category_id>", methods=["GET"])
def get_category(category_id):
    """
    Retrieve a specific category by its ID.
    
    Args:
        category_id (int): The unique ID of the category.
    
    Returns:
        JSON response with the category details, or 404 if not found.
    """
    category = Category.query.filter_by(id=category_id, is_active=True).first_or_404()
    
    logger.info(f"Retrieved category: {category.name}")
    return jsonify(category.to_dict(include_children=True)), 200

@app.route("/api/content/categories/<int:category_id>", methods=["PUT"])
@admin_required
def update_category(current_user_id, current_user_role, category_id):
    """
    Update an existing category.
    
    Args:
        category_id (int): The unique ID of the category to update.
    
    Request Body:
        name (str, optional): New name for the category.
        description (str, optional): New description for the category.
        parent_id (int, optional): New parent category ID.
    
    Returns:
        JSON response with success message and updated category, or error details.
    """
    category = Category.query.filter_by(id=category_id, is_active=True).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'name' in data:
        new_slug = slugify(data['name'])
        # Check if another category has this slug
        existing = Category.query.filter(Category.slug == new_slug, Category.id != category_id).first()
        if existing:
            return jsonify({"error": "Category with this name already exists"}), 409
        
        category.name = data['name']
        category.slug = new_slug
    
    if 'description' in data:
        category.description = data['description']
    
    if 'parent_id' in data:
        parent_id = data['parent_id']
        if parent_id:
            parent = Category.query.get(parent_id)
            if not parent:
                return jsonify({"error": "Parent category not found"}), 404
            # Prevent circular references
            if parent_id == category_id:
                return jsonify({"error": "Category cannot be its own parent"}), 400
        category.parent_id = parent_id
    
    db.session.commit()
    
    logger.info(f"Updated category: {category.name} by user {current_user_id}")
    return jsonify({
        "message": "Category updated successfully",
        "category": category.to_dict()
    }), 200

@app.route("/api/content/categories/<int:category_id>", methods=["DELETE"])
@admin_required
def delete_category(current_user_id, current_user_role, category_id):
    """
    Soft delete a category (mark as inactive).
    
    Args:
        category_id (int): The unique ID of the category to delete.
    
    Returns:
        JSON response with success message, or 404 if category not found.
    """
    category = Category.query.filter_by(id=category_id, is_active=True).first_or_404()
    
    # Check if category has articles
    if category.articles:
        return jsonify({
            "error": "Cannot delete category with associated articles. Please reassign articles first."
        }), 400
    
    # Check if category has child categories
    if category.children:
        return jsonify({
            "error": "Cannot delete category with child categories. Please reassign or delete child categories first."
        }), 400
    
    category.is_active = False
    db.session.commit()
    
    logger.info(f"Deleted category: {category.name} by user {current_user_id}")
    return jsonify({"message": "Category deleted successfully"}), 200

# --- Tag Management Endpoints ---
@app.route("/api/content/tags", methods=["POST"])
@admin_required
def create_tag(current_user_id, current_user_role):
    """
    Create a new content tag.
    
    Request Body:
        name (str): Display name of the tag.
        color (str, optional): Hex color code for the tag.
    
    Returns:
        JSON response with success message and the created tag, or error details.
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400
    
    # Generate slug from name
    slug = slugify(data['name'])
    
    # Check if a tag with this slug already exists
    if Tag.query.filter_by(slug=slug).first():
        return jsonify({"error": "Tag with this name already exists"}), 409
    
    new_tag = Tag(
        name=data['name'],
        slug=slug,
        color=data.get('color')
    )
    
    db.session.add(new_tag)
    db.session.commit()
    
    logger.info(f"Created new tag: {data['name']} by user {current_user_id}")
    return jsonify({
        "message": "Tag created successfully",
        "tag": new_tag.to_dict()
    }), 201

@app.route("/api/content/tags", methods=["GET"])
def get_tags():
    """
    Retrieve all active tags.
    
    Query Parameters:
        limit (int): Maximum number of tags to return.
        popular (bool): Order by usage count if true.
    
    Returns:
        JSON response with an array of tags.
    """
    limit = request.args.get('limit', type=int)
    popular = request.args.get('popular', 'false').lower() == 'true'
    
    query = Tag.query.filter_by(is_active=True)
    
    if popular:
        # Order by usage count (articles + pages)
        query = query.order_by(
            (db.func.count(Tag.articles) + db.func.count(Tag.pages)).desc()
        )
    else:
        query = query.order_by(Tag.name)
    
    if limit:
        query = query.limit(limit)
    
    tags = query.all()
    tags_data = [tag.to_dict() for tag in tags]
    
    logger.info(f"Retrieved {len(tags_data)} tags")
    return jsonify(tags_data), 200

@app.route("/api/content/tags/<int:tag_id>", methods=["PUT"])
@admin_required
def update_tag(current_user_id, current_user_role, tag_id):
    """
    Update an existing tag.
    
    Args:
        tag_id (int): The unique ID of the tag to update.
    
    Request Body:
        name (str, optional): New name for the tag.
        color (str, optional): New color for the tag.
    
    Returns:
        JSON response with success message and updated tag, or error details.
    """
    tag = Tag.query.filter_by(id=tag_id, is_active=True).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'name' in data:
        new_slug = slugify(data['name'])
        # Check if another tag has this slug
        existing = Tag.query.filter(Tag.slug == new_slug, Tag.id != tag_id).first()
        if existing:
            return jsonify({"error": "Tag with this name already exists"}), 409
        
        tag.name = data['name']
        tag.slug = new_slug
    
    if 'color' in data:
        tag.color = data['color']
    
    db.session.commit()
    
    logger.info(f"Updated tag: {tag.name} by user {current_user_id}")
    return jsonify({
        "message": "Tag updated successfully",
        "tag": tag.to_dict()
    }), 200

@app.route("/api/content/tags/<int:tag_id>", methods=["DELETE"])
@admin_required
def delete_tag(current_user_id, current_user_role, tag_id):
    """
    Soft delete a tag (mark as inactive).
    
    Args:
        tag_id (int): The unique ID of the tag to delete.
    
    Returns:
        JSON response with success message, or 404 if tag not found.
    """
    tag = Tag.query.filter_by(id=tag_id, is_active=True).first_or_404()
    
    tag.is_active = False
    db.session.commit()
    
    logger.info(f"Deleted tag: {tag.name} by user {current_user_id}")
    return jsonify({"message": "Tag deleted successfully"}), 200

# --- Media Management Endpoints ---
@app.route("/api/content/media", methods=["POST"])
@token_required
def upload_media(current_user_id, current_user_role):
    """
    Upload a media file.
    
    This endpoint handles file uploads and creates Media records.
    Supports images, videos, audio, and documents with automatic
    type detection and validation.
    
    Form Data:
        file: The file to upload.
        alt_text (optional): Alternative text for accessibility.
        caption (optional): Caption for the media.
    
    Returns:
        JSON response with uploaded media details, or error details.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Secure the filename
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    # Check file size (limit to 50MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > 50 * 1024 * 1024:  # 50MB
        return jsonify({"error": "File too large. Maximum size is 50MB"}), 413
    
    # Detect MIME type
    file_content = file.read()
    file.seek(0)
    mime_type = magic.from_buffer(file_content, mime=True)
    
    # Determine media type
    if mime_type.startswith('image/'):
        media_type = MediaType.IMAGE
    elif mime_type.startswith('video/'):
        media_type = MediaType.VIDEO
    elif mime_type.startswith('audio/'):
        media_type = MediaType.AUDIO
    elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        media_type = MediaType.DOCUMENT
    else:
        media_type = MediaType.OTHER
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(filename)[1]
    unique_filename = f"{file_id}{file_extension}"
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), media_type.value)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    file.save(file_path)
    
    # Create thumbnail for images
    if media_type == MediaType.IMAGE:
        try:
            create_thumbnail(file_path, upload_dir, file_id)
        except Exception as e:
            logger.warning(f"Failed to create thumbnail for {filename}: {e}")
    
    # Create Media record
    media = Media(
        id=file_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        media_type=media_type,
        alt_text=request.form.get('alt_text'),
        caption=request.form.get('caption'),
        uploaded_by=current_user_id
    )
    
    db.session.add(media)
    db.session.commit()
    
    logger.info(f"Uploaded media: {filename} by user {current_user_id}")
    return jsonify({
        "message": "Media uploaded successfully",
        "media": media.to_dict()
    }), 201

def create_thumbnail(file_path, upload_dir, file_id):
    """Create a thumbnail for an image file."""
    try:
        with Image.open(file_path) as img:
            # Create thumbnail (max 300x300)
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Save thumbnail
            thumbnail_path = os.path.join(upload_dir, f"{file_id}_thumb.jpg")
            img.save(thumbnail_path, "JPEG", quality=85)
            
    except Exception as e:
        logger.error(f"Failed to create thumbnail: {e}")
        raise

@app.route("/api/content/media", methods=["GET"])
def get_media():
    """
    Retrieve media files.
    
    Query Parameters:
        media_type (str): Filter by media type (image, video, audio, document, other).
        limit (int): Maximum number of media files to return.
        uploaded_by (str): Filter by uploader user ID.
    
    Returns:
        JSON response with an array of media files.
    """
    media_type = request.args.get('media_type')
    limit = request.args.get('limit', type=int)
    uploaded_by = request.args.get('uploaded_by')
    
    query = Media.query.filter_by(is_active=True)
    
    if media_type:
        try:
            media_type_enum = MediaType(media_type)
            query = query.filter_by(media_type=media_type_enum)
        except ValueError:
            return jsonify({"error": "Invalid media type"}), 400
    
    if uploaded_by:
        query = query.filter_by(uploaded_by=uploaded_by)
    
    query = query.order_by(Media.uploaded_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    media_files = query.all()
    media_data = [media.to_dict() for media in media_files]
    
    logger.info(f"Retrieved {len(media_data)} media files")
    return jsonify(media_data), 200

@app.route("/api/content/media/<media_id>", methods=["GET"])
def get_media_file(media_id):
    """
    Retrieve a specific media file by its ID.
    
    Args:
        media_id (str): The unique UUID of the media file.
    
    Returns:
        JSON response with the media file details, or 404 if not found.
    """
    try:
        media_uuid = uuid.UUID(media_id)
    except ValueError:
        return jsonify({"error": "Invalid media ID format"}), 400
    
    media = Media.query.filter_by(id=media_uuid, is_active=True).first_or_404()
    
    logger.info(f"Retrieved media: {media.filename}")
    return jsonify(media.to_dict()), 200

@app.route("/api/content/media/<media_id>/download", methods=["GET"])
def download_media(media_id):
    """
    Download a media file.
    
    Args:
        media_id (str): The unique UUID of the media file.
    
    Returns:
        File download response, or 404 if not found.
    """
    try:
        media_uuid = uuid.UUID(media_id)
    except ValueError:
        return jsonify({"error": "Invalid media ID format"}), 400
    
    media = Media.query.filter_by(id=media_uuid, is_active=True).first_or_404()
    
    if not os.path.exists(media.file_path):
        return jsonify({"error": "File not found on disk"}), 404
    
    logger.info(f"Downloaded media: {media.filename}")
    return send_file(media.file_path, as_attachment=True, download_name=media.filename)

@app.route("/api/content/media/<media_id>", methods=["PUT"])
@token_required
def update_media(current_user_id, current_user_role, media_id):
    """
    Update media metadata.
    
    Args:
        media_id (str): The unique UUID of the media file.
    
    Request Body:
        alt_text (str, optional): New alternative text.
        caption (str, optional): New caption.
    
    Returns:
        JSON response with success message and updated media, or error details.
    """
    try:
        media_uuid = uuid.UUID(media_id)
    except ValueError:
        return jsonify({"error": "Invalid media ID format"}), 400
    
    media = Media.query.filter_by(id=media_uuid, is_active=True).first_or_404()
    
    # Check if user owns the media or is admin
    if media.uploaded_by != current_user_id and current_user_role not in ['admin', 'moderator']:
        return jsonify({"error": "Permission denied"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'alt_text' in data:
        media.alt_text = data['alt_text']
    
    if 'caption' in data:
        media.caption = data['caption']
    
    db.session.commit()
    
    logger.info(f"Updated media: {media.filename} by user {current_user_id}")
    return jsonify({
        "message": "Media updated successfully",
        "media": media.to_dict()
    }), 200

@app.route("/api/content/media/<media_id>", methods=["DELETE"])
@token_required
def delete_media(current_user_id, current_user_role, media_id):
    """
    Soft delete a media file (mark as inactive).
    
    Args:
        media_id (str): The unique UUID of the media file.
    
    Returns:
        JSON response with success message, or 404 if media not found.
    """
    try:
        media_uuid = uuid.UUID(media_id)
    except ValueError:
        return jsonify({"error": "Invalid media ID format"}), 400
    
    media = Media.query.filter_by(id=media_uuid, is_active=True).first_or_404()
    
    # Check if user owns the media or is admin
    if media.uploaded_by != current_user_id and current_user_role not in ['admin', 'moderator']:
        return jsonify({"error": "Permission denied"}), 403
    
    media.is_active = False
    db.session.commit()
    
    logger.info(f"Deleted media: {media.filename} by user {current_user_id}")
    return jsonify({"message": "Media deleted successfully"}), 200

# --- Enhanced ContentPage Endpoints ---
@app.route("/api/content/pages", methods=["POST"])
@token_required
def create_content_page(current_user_id, current_user_role):
    """
    Create a new static content page with enhanced features.
    
    Request Body:
        title (str): Display title of the page.
        content (str): Main content of the page (HTML or markdown).
        excerpt (str, optional): Short summary of the page.
        slug (str, optional): Custom URL slug (auto-generated if not provided).
        status (str, optional): Content status (default: draft).
        featured_image_id (str, optional): UUID of featured image.
        meta_title (str, optional): SEO meta title.
        meta_description (str, optional): SEO meta description.
        meta_keywords (str, optional): SEO meta keywords.
        tag_ids (list, optional): List of tag IDs to associate with the page.
    
    Returns:
        JSON response with success message and the created page, or error details.
    """
    data = request.get_json()
    if not data or not all(key in data for key in ["title", "content"]):
        return jsonify({"error": "Missing required fields: title, content"}), 400
    
    # Generate slug if not provided
    slug = data.get('slug', slugify(data['title']))
    
    # Check if a page with this slug already exists
    if ContentPage.query.filter_by(slug=slug).first():
        return jsonify({"error": "Page with this slug already exists"}), 409
    
    # Validate status
    status = ContentStatus.DRAFT
    if 'status' in data:
        try:
            status = ContentStatus(data['status'])
        except ValueError:
            return jsonify({"error": "Invalid status value"}), 400
    
    # Validate featured image if provided
    featured_image_id = None
    if 'featured_image_id' in data:
        try:
            featured_image_id = uuid.UUID(data['featured_image_id'])
            if not Media.query.filter_by(id=featured_image_id, is_active=True).first():
                return jsonify({"error": "Featured image not found"}), 404
        except ValueError:
            return jsonify({"error": "Invalid featured image ID format"}), 400
    
    new_page = ContentPage(
        slug=slug,
        title=data['title'],
        content=data['content'],
        excerpt=data.get('excerpt'),
        status=status,
        featured_image_id=featured_image_id,
        meta_title=data.get('meta_title'),
        meta_description=data.get('meta_description'),
        meta_keywords=data.get('meta_keywords'),
        created_by=current_user_id
    )
    
    db.session.add(new_page)
    db.session.flush()  # Get the ID before committing
    
    # Associate tags if provided
    if 'tag_ids' in data and data['tag_ids']:
        tags = Tag.query.filter(Tag.id.in_(data['tag_ids']), Tag.is_active == True).all()
        new_page.tags = tags
    
    db.session.commit()
    
    logger.info(f"Created new content page: {data['title']} by user {current_user_id}")
    return jsonify({
        "message": "Content page created successfully",
        "page": new_page.to_dict(include_tags=True)
    }), 201

@app.route("/api/content/pages", methods=["GET"])
def get_content_pages():
    """
    Retrieve content pages with enhanced filtering and pagination.
    
    Query Parameters:
        status (str): Filter by content status.
        tag (str): Filter by tag slug.
        limit (int): Maximum number of pages to return.
        offset (int): Number of pages to skip.
        include_content (bool): Include full content in response.
        search (str): Search in title and content.
    
    Returns:
        JSON response with an array of content pages and pagination info.
    """
    status = request.args.get('status')
    tag_slug = request.args.get('tag')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    include_content = request.args.get('include_content', 'false').lower() == 'true'
    search = request.args.get('search')
    
    query = ContentPage.query
    
    # Filter by status
    if status:
        try:
            status_enum = ContentStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            return jsonify({"error": "Invalid status value"}), 400
    else:
        # Default to published pages for public access
        query = query.filter_by(status=ContentStatus.PUBLISHED)
    
    # Filter by tag
    if tag_slug:
        tag = Tag.query.filter_by(slug=tag_slug, is_active=True).first()
        if tag:
            query = query.filter(ContentPage.tags.contains(tag))
        else:
            return jsonify({"error": "Tag not found"}), 404
    
    # Search functionality
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                ContentPage.title.ilike(search_term),
                ContentPage.content.ilike(search_term),
                ContentPage.excerpt.ilike(search_term)
            )
        )
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    pages = query.order_by(ContentPage.updated_at.desc()).offset(offset).limit(limit).all()
    
    pages_data = [page.to_dict(include_content=include_content, include_tags=True) for page in pages]
    
    logger.info(f"Retrieved {len(pages_data)} content pages (total: {total_count})")
    return jsonify({
        "pages": pages_data,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }), 200

@app.route("/api/content/pages/<slug>", methods=["GET"])
def get_content_page(slug):
    """
    Retrieve a specific content page by its slug with enhanced details.
    
    Args:
        slug (str): The unique slug identifier of the content page.
    
    Query Parameters:
        include_versions (bool): Include version history in response.
    
    Returns:
        JSON response with the content page details, or 404 if not found.
    """
    include_versions = request.args.get('include_versions', 'false').lower() == 'true'
    
    page = ContentPage.query.filter_by(slug=slug, status=ContentStatus.PUBLISHED).first_or_404()
    
    result = page.to_dict(include_content=True, include_tags=True)
    
    if include_versions:
        versions = ContentVersion.query.filter_by(content_page_id=page.id).order_by(
            ContentVersion.version_number.desc()
        ).limit(10).all()
        result['versions'] = [version.to_dict() for version in versions]
    
    logger.info(f"Retrieved content page: {slug}")
    return jsonify(result), 200

@app.route("/api/content/pages/<slug>", methods=["PUT"])
@token_required
def update_content_page(current_user_id, current_user_role, slug):
    """
    Update an existing content page with enhanced features.
    
    Args:
        slug (str): The unique slug identifier of the content page to update.
    
    Request Body:
        title (str, optional): New title for the page.
        content (str, optional): New content for the page.
        excerpt (str, optional): New excerpt for the page.
        featured_image_id (str, optional): New featured image UUID.
        meta_title (str, optional): New SEO meta title.
        meta_description (str, optional): New SEO meta description.
        meta_keywords (str, optional): New SEO meta keywords.
        tag_ids (list, optional): New list of tag IDs.
    
    Returns:
        JSON response with success message and updated page, or error details.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    
    # Check permissions
    if page.created_by != current_user_id and current_user_role not in ['admin', 'moderator']:
        return jsonify({"error": "Permission denied"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate featured image if provided
    if 'featured_image_id' in data and data['featured_image_id']:
        try:
            featured_image_id = uuid.UUID(data['featured_image_id'])
            if not Media.query.filter_by(id=featured_image_id, is_active=True).first():
                return jsonify({"error": "Featured image not found"}), 404
            data['featured_image_id'] = featured_image_id
        except ValueError:
            return jsonify({"error": "Invalid featured image ID format"}), 400
    
    # Update the page using the model method
    page.update_content(
        title=data.get("title"),
        content=data.get("content"),
        excerpt=data.get("excerpt"),
        updated_by=current_user_id,
        meta_title=data.get("meta_title"),
        meta_description=data.get("meta_description"),
        meta_keywords=data.get("meta_keywords")
    )
    
    # Update featured image
    if 'featured_image_id' in data:
        page.featured_image_id = data['featured_image_id']
    
    # Update tags if provided
    if 'tag_ids' in data:
        if data['tag_ids']:
            tags = Tag.query.filter(Tag.id.in_(data['tag_ids']), Tag.is_active == True).all()
            page.tags = tags
        else:
            page.tags = []
    
    db.session.commit()
    
    logger.info(f"Updated content page: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Content page updated successfully",
        "page": page.to_dict(include_tags=True)
    }), 200

@app.route("/api/content/pages/<slug>/publish", methods=["POST"])
@admin_required
def publish_content_page(current_user_id, current_user_role, slug):
    """
    Publish a content page.
    
    Args:
        slug (str): The unique slug identifier of the content page to publish.
    
    Returns:
        JSON response with success message, or error details.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    
    if page.status == ContentStatus.PUBLISHED:
        return jsonify({"error": "Page is already published"}), 400
    
    page.publish(published_by=current_user_id)
    db.session.commit()
    
    logger.info(f"Published content page: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Content page published successfully",
        "page": page.to_dict()
    }), 200

@app.route("/api/content/pages/<slug>/archive", methods=["POST"])
@admin_required
def archive_content_page(current_user_id, current_user_role, slug):
    """
    Archive a content page.
    
    Args:
        slug (str): The unique slug identifier of the content page to archive.
    
    Returns:
        JSON response with success message, or error details.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    
    if page.status == ContentStatus.ARCHIVED:
        return jsonify({"error": "Page is already archived"}), 400
    
    page.archive(archived_by=current_user_id)
    db.session.commit()
    
    logger.info(f"Archived content page: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Content page archived successfully",
        "page": page.to_dict()
    }), 200

@app.route("/api/content/pages/<slug>", methods=["DELETE"])
@admin_required
def delete_content_page(current_user_id, current_user_role, slug):
    """
    Permanently delete a content page.
    
    Args:
        slug (str): The unique slug identifier of the content page to delete.
    
    Returns:
        JSON response with success message, or 404 if page not found.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    page_title = page.title  # Store for logging before deletion
    
    db.session.delete(page)
    db.session.commit()
    
    logger.info(f"Deleted content page: {page_title} by user {current_user_id}")
    return jsonify({"message": "Content page deleted successfully"}), 200

# --- Enhanced Article Endpoints ---
@app.route("/api/content/articles", methods=["POST"])
@token_required
def create_article(current_user_id, current_user_role):
    """
    Create a new article with enhanced features.
    
    Request Body:
        title (str): Title of the article.
        content (str): Main content of the article (HTML or markdown).
        excerpt (str, optional): Short summary of the article.
        author (str, optional): Name of the article author.
        slug (str, optional): Custom URL slug (auto-generated if not provided).
        status (str, optional): Content status (default: draft).
        featured_image_id (str, optional): UUID of featured image.
        category_ids (list, optional): List of category IDs.
        tag_ids (list, optional): List of tag IDs.
        meta_title (str, optional): SEO meta title.
        meta_description (str, optional): SEO meta description.
        meta_keywords (str, optional): SEO meta keywords.
    
    Returns:
        JSON response with success message and the created article, or error details.
    """
    data = request.get_json()
    if not data or not all(key in data for key in ["title", "content"]):
        return jsonify({"error": "Missing required fields: title, content"}), 400
    
    # Generate slug if not provided
    slug = data.get('slug', slugify(data['title']))
    
    # Check if an article with this slug already exists
    if Article.query.filter_by(slug=slug).first():
        return jsonify({"error": "Article with this slug already exists"}), 409
    
    # Validate status
    status = ContentStatus.DRAFT
    if 'status' in data:
        try:
            status = ContentStatus(data['status'])
        except ValueError:
            return jsonify({"error": "Invalid status value"}), 400
    
    # Validate featured image if provided
    featured_image_id = None
    if 'featured_image_id' in data:
        try:
            featured_image_id = uuid.UUID(data['featured_image_id'])
            if not Media.query.filter_by(id=featured_image_id, is_active=True).first():
                return jsonify({"error": "Featured image not found"}), 404
        except ValueError:
            return jsonify({"error": "Invalid featured image ID format"}), 400
    
    new_article = Article(
        title=data['title'],
        slug=slug,
        content=data['content'],
        excerpt=data.get('excerpt'),
        author=data.get('author'),
        status=status,
        featured_image_id=featured_image_id,
        meta_title=data.get('meta_title'),
        meta_description=data.get('meta_description'),
        meta_keywords=data.get('meta_keywords'),
        created_by=current_user_id
    )
    
    db.session.add(new_article)
    db.session.flush()  # Get the ID before committing
    
    # Associate categories if provided
    if 'category_ids' in data and data['category_ids']:
        categories = Category.query.filter(
            Category.id.in_(data['category_ids']), 
            Category.is_active == True
        ).all()
        new_article.categories = categories
    
    # Associate tags if provided
    if 'tag_ids' in data and data['tag_ids']:
        tags = Tag.query.filter(Tag.id.in_(data['tag_ids']), Tag.is_active == True).all()
        new_article.tags = tags
    
    db.session.commit()
    
    logger.info(f"Created new article: {data['title']} by user {current_user_id}")
    return jsonify({
        "message": "Article created successfully",
        "article": new_article.to_dict(include_categories=True, include_tags=True)
    }), 201

@app.route("/api/content/articles", methods=["GET"])
def get_articles():
    """
    Retrieve articles with enhanced filtering and pagination.
    
    Query Parameters:
        status (str): Filter by content status.
        category (str): Filter by category slug.
        tag (str): Filter by tag slug.
        author (str): Filter by author name.
        limit (int): Maximum number of articles to return.
        offset (int): Number of articles to skip.
        include_content (bool): Include full content in response.
        search (str): Search in title and content.
        popular (bool): Order by view count if true.
    
    Returns:
        JSON response with an array of articles and pagination info.
    """
    status = request.args.get('status')
    category_slug = request.args.get('category')
    tag_slug = request.args.get('tag')
    author = request.args.get('author')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    include_content = request.args.get('include_content', 'false').lower() == 'true'
    search = request.args.get('search')
    popular = request.args.get('popular', 'false').lower() == 'true'
    
    query = Article.query
    
    # Filter by status
    if status:
        try:
            status_enum = ContentStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            return jsonify({"error": "Invalid status value"}), 400
    else:
        # Default to published articles for public access
        query = query.filter_by(status=ContentStatus.PUBLISHED)
    
    # Filter by category
    if category_slug:
        category = Category.query.filter_by(slug=category_slug, is_active=True).first()
        if category:
            query = query.filter(Article.categories.contains(category))
        else:
            return jsonify({"error": "Category not found"}), 404
    
    # Filter by tag
    if tag_slug:
        tag = Tag.query.filter_by(slug=tag_slug, is_active=True).first()
        if tag:
            query = query.filter(Article.tags.contains(tag))
        else:
            return jsonify({"error": "Tag not found"}), 404
    
    # Filter by author
    if author:
        query = query.filter_by(author=author)
    
    # Search functionality
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Article.title.ilike(search_term),
                Article.content.ilike(search_term),
                Article.excerpt.ilike(search_term),
                Article.author.ilike(search_term)
            )
        )
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply ordering
    if popular:
        query = query.order_by(Article.view_count.desc())
    else:
        query = query.order_by(Article.published_at.desc())
    
    # Apply pagination
    articles = query.offset(offset).limit(limit).all()
    
    articles_data = [
        article.to_dict(
            include_content=include_content, 
            include_categories=True, 
            include_tags=True
        ) for article in articles
    ]
    
    logger.info(f"Retrieved {len(articles_data)} articles (total: {total_count})")
    return jsonify({
        "articles": articles_data,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }), 200

@app.route("/api/content/articles/<slug>", methods=["GET"])
def get_article_by_slug(slug):
    """
    Retrieve a specific article by its slug with enhanced details.
    
    Args:
        slug (str): The unique slug identifier of the article.
    
    Query Parameters:
        include_versions (bool): Include version history in response.
        increment_views (bool): Increment view count (default: true).
    
    Returns:
        JSON response with the article details, or 404 if not found.
    """
    include_versions = request.args.get('include_versions', 'false').lower() == 'true'
    increment_views = request.args.get('increment_views', 'true').lower() == 'true'
    
    article = Article.query.filter_by(slug=slug, status=ContentStatus.PUBLISHED).first_or_404()
    
    # Increment view count
    if increment_views:
        article.increment_view_count()
        db.session.commit()
    
    result = article.to_dict(include_content=True, include_categories=True, include_tags=True)
    
    if include_versions:
        versions = ContentVersion.query.filter_by(article_id=article.id).order_by(
            ContentVersion.version_number.desc()
        ).limit(10).all()
        result['versions'] = [version.to_dict() for version in versions]
    
    logger.info(f"Retrieved article: {slug}")
    return jsonify(result), 200

@app.route("/api/content/articles/<int:article_id>", methods=["GET"])
def get_article(article_id):
    """
    Retrieve a specific article by its ID with enhanced details.
    
    Args:
        article_id (int): The unique ID of the article.
    
    Returns:
        JSON response with the article details, or 404 if not found.
    """
    article = Article.query.filter_by(id=article_id, status=ContentStatus.PUBLISHED).first_or_404()
    
    # Increment view count
    article.increment_view_count()
    db.session.commit()
    
    logger.info(f"Retrieved article: {article.title}")
    return jsonify(article.to_dict(include_content=True, include_categories=True, include_tags=True)), 200

@app.route("/api/content/articles/<slug>", methods=["PUT"])
@token_required
def update_article_by_slug(current_user_id, current_user_role, slug):
    """
    Update an existing article by slug with enhanced features.
    
    Args:
        slug (str): The unique slug identifier of the article to update.
    
    Request Body:
        title (str, optional): New title for the article.
        content (str, optional): New content for the article.
        excerpt (str, optional): New excerpt for the article.
        author (str, optional): New author for the article.
        featured_image_id (str, optional): New featured image UUID.
        category_ids (list, optional): New list of category IDs.
        tag_ids (list, optional): New list of tag IDs.
        meta_title (str, optional): New SEO meta title.
        meta_description (str, optional): New SEO meta description.
        meta_keywords (str, optional): New SEO meta keywords.
    
    Returns:
        JSON response with success message and updated article, or error details.
    """
    article = Article.query.filter_by(slug=slug).first_or_404()
    
    # Check permissions
    if article.created_by != current_user_id and current_user_role not in ['admin', 'moderator']:
        return jsonify({"error": "Permission denied"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate featured image if provided
    if 'featured_image_id' in data and data['featured_image_id']:
        try:
            featured_image_id = uuid.UUID(data['featured_image_id'])
            if not Media.query.filter_by(id=featured_image_id, is_active=True).first():
                return jsonify({"error": "Featured image not found"}), 404
            data['featured_image_id'] = featured_image_id
        except ValueError:
            return jsonify({"error": "Invalid featured image ID format"}), 400
    
    # Update the article using the model method
    article.update_article(
        title=data.get("title"),
        content=data.get("content"),
        excerpt=data.get("excerpt"),
        author=data.get("author"),
        updated_by=current_user_id,
        meta_title=data.get("meta_title"),
        meta_description=data.get("meta_description"),
        meta_keywords=data.get("meta_keywords")
    )
    
    # Update featured image
    if 'featured_image_id' in data:
        article.featured_image_id = data['featured_image_id']
    
    # Update categories if provided
    if 'category_ids' in data:
        if data['category_ids']:
            categories = Category.query.filter(
                Category.id.in_(data['category_ids']), 
                Category.is_active == True
            ).all()
            article.categories = categories
        else:
            article.categories = []
    
    # Update tags if provided
    if 'tag_ids' in data:
        if data['tag_ids']:
            tags = Tag.query.filter(Tag.id.in_(data['tag_ids']), Tag.is_active == True).all()
            article.tags = tags
        else:
            article.tags = []
    
    db.session.commit()
    
    logger.info(f"Updated article: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Article updated successfully",
        "article": article.to_dict(include_categories=True, include_tags=True)
    }), 200

@app.route("/api/content/articles/<slug>/publish", methods=["POST"])
@admin_required
def publish_article(current_user_id, current_user_role, slug):
    """
    Publish an article.
    
    Args:
        slug (str): The unique slug identifier of the article to publish.
    
    Returns:
        JSON response with success message, or error details.
    """
    article = Article.query.filter_by(slug=slug).first_or_404()
    
    if article.status == ContentStatus.PUBLISHED:
        return jsonify({"error": "Article is already published"}), 400
    
    article.publish(published_by=current_user_id)
    db.session.commit()
    
    logger.info(f"Published article: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Article published successfully",
        "article": article.to_dict()
    }), 200

@app.route("/api/content/articles/<slug>/archive", methods=["POST"])
@admin_required
def archive_article(current_user_id, current_user_role, slug):
    """
    Archive an article.
    
    Args:
        slug (str): The unique slug identifier of the article to archive.
    
    Returns:
        JSON response with success message, or error details.
    """
    article = Article.query.filter_by(slug=slug).first_or_404()
    
    if article.status == ContentStatus.ARCHIVED:
        return jsonify({"error": "Article is already archived"}), 400
    
    article.archive(archived_by=current_user_id)
    db.session.commit()
    
    logger.info(f"Archived article: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Article archived successfully",
        "article": article.to_dict()
    }), 200

@app.route("/api/content/articles/<slug>/like", methods=["POST"])
@token_required
def like_article(current_user_id, current_user_role, slug):
    """
    Like an article (increment like count).
    
    Args:
        slug (str): The unique slug identifier of the article to like.
    
    Returns:
        JSON response with success message and updated like count.
    """
    article = Article.query.filter_by(slug=slug, status=ContentStatus.PUBLISHED).first_or_404()
    
    article.increment_like_count()
    db.session.commit()
    
    logger.info(f"Liked article: {slug} by user {current_user_id}")
    return jsonify({
        "message": "Article liked successfully",
        "like_count": article.like_count
    }), 200

@app.route("/api/content/articles/<slug>", methods=["DELETE"])
@admin_required
def delete_article_by_slug(current_user_id, current_user_role, slug):
    """
    Permanently delete an article by slug.
    
    Args:
        slug (str): The unique slug identifier of the article to delete.
    
    Returns:
        JSON response with success message, or 404 if article not found.
    """
    article = Article.query.filter_by(slug=slug).first_or_404()
    article_title = article.title  # Store for logging before deletion
    
    db.session.delete(article)
    db.session.commit()
    
    logger.info(f"Deleted article: {article_title} by user {current_user_id}")
    return jsonify({"message": "Article deleted successfully"}), 200

# --- Search Endpoint ---
@app.route("/api/content/search", methods=["GET"])
def search_content():
    """
    Search across all content types using full-text search.
    
    Query Parameters:
        q (str): Search query.
        type (str): Content type filter (page, article, all).
        limit (int): Maximum number of results to return.
        offset (int): Number of results to skip.
    
    Returns:
        JSON response with search results and pagination info.
    """
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    content_type = request.args.get('type', 'all')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    results = []
    total_count = 0
    
    if content_type in ['all', 'page']:
        # Search content pages
        page_query = ContentPage.query.filter(
            ContentPage.status == ContentStatus.PUBLISHED,
            db.or_(
                ContentPage.title.ilike(f"%{query}%"),
                ContentPage.content.ilike(f"%{query}%"),
                ContentPage.excerpt.ilike(f"%{query}%")
            )
        )
        
        page_count = page_query.count()
        pages = page_query.order_by(ContentPage.updated_at.desc()).offset(offset).limit(limit).all()
        
        for page in pages:
            result = page.to_dict(include_content=False, include_tags=True)
            result['content_type'] = 'page'
            results.append(result)
        
        total_count += page_count
    
    if content_type in ['all', 'article']:
        # Search articles
        article_query = Article.query.filter(
            Article.status == ContentStatus.PUBLISHED,
            db.or_(
                Article.title.ilike(f"%{query}%"),
                Article.content.ilike(f"%{query}%"),
                Article.excerpt.ilike(f"%{query}%"),
                Article.author.ilike(f"%{query}%")
            )
        )
        
        article_count = article_query.count()
        articles = article_query.order_by(Article.published_at.desc()).offset(offset).limit(limit).all()
        
        for article in articles:
            result = article.to_dict(include_content=False, include_categories=True, include_tags=True)
            result['content_type'] = 'article'
            results.append(result)
        
        total_count += article_count
    
    # Sort results by relevance (for now, by updated/published date)
    results.sort(key=lambda x: x.get('updated_at', x.get('published_at', '')), reverse=True)
    
    # Apply pagination to combined results
    paginated_results = results[offset:offset + limit]
    
    logger.info(f"Search for '{query}' returned {len(paginated_results)} results (total: {total_count})")
    return jsonify({
        "results": paginated_results,
        "query": query,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }), 200

# --- Version Management Endpoints ---
@app.route("/api/content/pages/<slug>/versions", methods=["GET"])
@token_required
def get_page_versions(current_user_id, current_user_role, slug):
    """
    Get version history for a content page.
    
    Args:
        slug (str): The unique slug identifier of the content page.
    
    Returns:
        JSON response with version history.
    """
    page = ContentPage.query.filter_by(slug=slug).first_or_404()
    
    # Check permissions
    if page.created_by != current_user_id and current_user_role not in ['admin', 'moderator']:
        return jsonify({"error": "Permission denied"}), 403
    
    versions = ContentVersion.query.filter_by(content_page_id=page.id).order_by(
        ContentVersion.version_number.desc()
    ).all()
    
    versions_data = [version.to_dict() for version in versions]
    
    logger.info(f"Retrieved {len(versions_data)} versions for page: {slug}")
    return jsonify(versions_data), 200

@app.route("/api/content/articles/<slug>/versions", methods=["GET"])
@token_required
def get_article_versions(current_user_id, current_user_role, slug):
    """
    Get version history for an article.
    
    Args:
        slug (str): The unique slug identifier of the article.
    
    Returns:
        JSON response with version history.
    """
    article = Article.query.filter_by(slug=slug).first_or_404()
    
    # Check permissions
    if article.created_by != current_user_id and current_user_role not in ['admin', 'moderator']:
        return jsonify({"error": "Permission denied"}), 403
    
    versions = ContentVersion.query.filter_by(article_id=article.id).order_by(
        ContentVersion.version_number.desc()
    ).all()
    
    versions_data = [version.to_dict() for version in versions]
    
    logger.info(f"Retrieved {len(versions_data)} versions for article: {slug}")
    return jsonify(versions_data), 200

@app.route("/api/content/versions/<int:version_id>/restore", methods=["POST"])
@admin_required
def restore_version(current_user_id, current_user_role, version_id):
    """
    Restore content to a previous version.
    
    Args:
        version_id (int): The unique ID of the version to restore.
    
    Returns:
        JSON response with success message, or error details.
    """
    version = ContentVersion.query.get_or_404(version_id)
    
    if version.content_page_id:
        # Restore content page
        page = ContentPage.query.get(version.content_page_id)
        if not page:
            return jsonify({"error": "Content page not found"}), 404
        
        page.update_content(
            title=version.title,
            content=version.content,
            excerpt=version.excerpt,
            updated_by=current_user_id,
            meta_title=version.meta_title,
            meta_description=version.meta_description,
            meta_keywords=version.meta_keywords
        )
        
        content_type = "page"
        content_title = page.title
        
    elif version.article_id:
        # Restore article
        article = Article.query.get(version.article_id)
        if not article:
            return jsonify({"error": "Article not found"}), 404
        
        article.update_article(
            title=version.title,
            content=version.content,
            excerpt=version.excerpt,
            updated_by=current_user_id,
            meta_title=version.meta_title,
            meta_description=version.meta_description,
            meta_keywords=version.meta_keywords
        )
        
        content_type = "article"
        content_title = article.title
    
    else:
        return jsonify({"error": "Invalid version"}), 400
    
    db.session.commit()
    
    logger.info(f"Restored {content_type} '{content_title}' to version {version.version_number} by user {current_user_id}")
    return jsonify({
        "message": f"Content restored to version {version.version_number} successfully"
    }), 200

# --- Analytics Endpoints ---
@app.route("/api/content/analytics/popular", methods=["GET"])
def get_popular_content():
    """
    Get popular content based on view counts.
    
    Query Parameters:
        type (str): Content type (page, article, all).
        limit (int): Maximum number of items to return.
        days (int): Number of days to consider (not implemented yet).
    
    Returns:
        JSON response with popular content.
    """
    content_type = request.args.get('type', 'all')
    limit = request.args.get('limit', 10, type=int)
    
    results = []
    
    if content_type in ['all', 'article']:
        # Get popular articles
        popular_articles = Article.get_popular_articles(limit=limit)
        for article in popular_articles:
            result = article.to_dict(include_content=False, include_categories=True, include_tags=True)
            result['content_type'] = 'article'
            results.append(result)
    
    if content_type in ['all', 'page']:
        # Get popular pages (for now, just recent ones since pages don't have view counts yet)
        popular_pages = ContentPage.query.filter_by(status=ContentStatus.PUBLISHED).order_by(
            ContentPage.updated_at.desc()
        ).limit(limit).all()
        
        for page in popular_pages:
            result = page.to_dict(include_content=False, include_tags=True)
            result['content_type'] = 'page'
            results.append(result)
    
    # Sort by view count if available
    results.sort(key=lambda x: x.get('view_count', 0), reverse=True)
    
    logger.info(f"Retrieved {len(results)} popular content items")
    return jsonify(results[:limit]), 200

@app.route("/api/content/analytics/stats", methods=["GET"])
@admin_required
def get_content_stats(current_user_id, current_user_role):
    """
    Get content statistics for admin dashboard.
    
    Returns:
        JSON response with content statistics.
    """
    stats = {
        "articles": {
            "total": Article.query.count(),
            "published": Article.query.filter_by(status=ContentStatus.PUBLISHED).count(),
            "draft": Article.query.filter_by(status=ContentStatus.DRAFT).count(),
            "pending": Article.query.filter_by(status=ContentStatus.PENDING).count(),
            "archived": Article.query.filter_by(status=ContentStatus.ARCHIVED).count(),
        },
        "pages": {
            "total": ContentPage.query.count(),
            "published": ContentPage.query.filter_by(status=ContentStatus.PUBLISHED).count(),
            "draft": ContentPage.query.filter_by(status=ContentStatus.DRAFT).count(),
            "pending": ContentPage.query.filter_by(status=ContentStatus.PENDING).count(),
            "archived": ContentPage.query.filter_by(status=ContentStatus.ARCHIVED).count(),
        },
        "categories": {
            "total": Category.query.count(),
            "active": Category.query.filter_by(is_active=True).count(),
        },
        "tags": {
            "total": Tag.query.count(),
            "active": Tag.query.filter_by(is_active=True).count(),
        },
        "media": {
            "total": Media.query.count(),
            "active": Media.query.filter_by(is_active=True).count(),
            "images": Media.query.filter_by(media_type=MediaType.IMAGE, is_active=True).count(),
            "videos": Media.query.filter_by(media_type=MediaType.VIDEO, is_active=True).count(),
            "documents": Media.query.filter_by(media_type=MediaType.DOCUMENT, is_active=True).count(),
        }
    }
    
    logger.info(f"Retrieved content statistics for user {current_user_id}")
    return jsonify(stats), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(RequestEntityTooLarge)
def file_too_large(error):
    return jsonify({"error": "File too large"}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
