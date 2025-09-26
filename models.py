"""
Content Service Data Models - Naebak Project

This module defines the database models for the Naebak Content Service.
It includes models for managing static content pages, dynamic articles,
content organization (categories and tags), versioning, media management,
and content moderation workflow.
"""

from datetime import datetime
from enum import Enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, text
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
import uuid

db = SQLAlchemy()

class ContentStatus(Enum):
    """
    Enumeration for content status in the moderation workflow.
    
    This enum defines the possible states of content in the system,
    supporting a complete content moderation and publishing workflow.
    """
    DRAFT = "draft"           # Content is being written/edited
    PENDING = "pending"       # Content is awaiting moderation
    PUBLISHED = "published"   # Content is live and visible to users
    ARCHIVED = "archived"     # Content is no longer active but preserved
    REJECTED = "rejected"     # Content was rejected during moderation

class MediaType(Enum):
    """
    Enumeration for different types of media files.
    """
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"

# Association tables for many-to-many relationships
article_categories = db.Table('article_categories',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

article_tags = db.Table('article_tags',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

page_tags = db.Table('page_tags',
    db.Column('page_id', db.Integer, db.ForeignKey('content_page.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Category(db.Model):
    """
    Represents a content category for organizing articles.
    
    Categories provide a hierarchical way to organize content, supporting
    parent-child relationships for nested categorization.
    
    Attributes:
        id (int): Primary key identifier.
        name (str): Display name of the category.
        slug (str): URL-friendly identifier.
        description (str): Optional description of the category.
        parent_id (int): Reference to parent category for hierarchy.
        created_at (datetime): When the category was created.
        is_active (bool): Whether the category is currently active.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Self-referential relationship for hierarchy
    parent = db.relationship('Category', remote_side=[id], backref='children')
    
    # Relationship with articles
    articles = db.relationship('Article', secondary=article_categories, back_populates='categories')
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self, include_children=False):
        """Convert category to dictionary for JSON serialization."""
        result = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'article_count': len(self.articles)
        }
        
        if include_children:
            result['children'] = [child.to_dict() for child in self.children if child.is_active]
        
        return result

class Tag(db.Model):
    """
    Represents a content tag for flexible content labeling.
    
    Tags provide a non-hierarchical way to label and organize content,
    allowing for flexible content discovery and filtering.
    
    Attributes:
        id (int): Primary key identifier.
        name (str): Display name of the tag.
        slug (str): URL-friendly identifier.
        color (str): Optional color code for UI display.
        created_at (datetime): When the tag was created.
        is_active (bool): Whether the tag is currently active.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7))  # Hex color code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    articles = db.relationship('Article', secondary=article_tags, back_populates='tags')
    pages = db.relationship('ContentPage', secondary=page_tags, back_populates='tags')
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
    def to_dict(self):
        """Convert tag to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'color': self.color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'usage_count': len(self.articles) + len(self.pages)
        }

class Media(db.Model):
    """
    Represents uploaded media files (images, videos, documents, etc.).
    
    This model manages all media assets used in content, providing
    metadata, file management, and usage tracking capabilities.
    
    Attributes:
        id (UUID): Primary key identifier.
        filename (str): Original filename of the uploaded file.
        file_path (str): Storage path of the file.
        file_size (int): Size of the file in bytes.
        mime_type (str): MIME type of the file.
        media_type (MediaType): Category of media (image, video, etc.).
        alt_text (str): Alternative text for accessibility.
        caption (str): Optional caption for the media.
        uploaded_by (str): ID of the user who uploaded the file.
        uploaded_at (datetime): When the file was uploaded.
        is_active (bool): Whether the media is currently active.
    """
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    media_type = db.Column(db.Enum(MediaType), nullable=False)
    alt_text = db.Column(db.String(255))
    caption = db.Column(db.Text)
    uploaded_by = db.Column(db.String(100))  # User ID from auth service
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Media {self.filename}>'
    
    def to_dict(self):
        """Convert media to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'media_type': self.media_type.value,
            'alt_text': self.alt_text,
            'caption': self.caption,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'is_active': self.is_active
        }

class ContentPage(db.Model):
    """
    Represents a static content page in the system.
    
    Enhanced ContentPage model with SEO support, versioning, moderation workflow,
    and improved content organization capabilities.
    
    Attributes:
        id (int): The primary key identifier for the content page.
        slug (str): A unique, URL-friendly identifier for the page.
        title (str): The display title of the content page.
        content (str): The main content of the page, stored as HTML or markdown.
        excerpt (str): Short summary or excerpt of the page content.
        status (ContentStatus): Current status in the moderation workflow.
        featured_image_id (UUID): Reference to featured image in Media table.
        
        # SEO fields
        meta_title (str): SEO meta title (overrides title if set).
        meta_description (str): SEO meta description.
        meta_keywords (str): SEO meta keywords.
        
        # Timestamps
        created_at (datetime): When the page was created.
        updated_at (datetime): When the page was last modified.
        published_at (datetime): When the page was published.
        
        # Moderation fields
        created_by (str): ID of the user who created the page.
        updated_by (str): ID of the user who last updated the page.
        moderated_by (str): ID of the moderator who reviewed the page.
        moderation_notes (str): Notes from the moderation process.
        
        # Search and indexing
        search_vector (TSVECTOR): Full-text search vector for PostgreSQL.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    status = db.Column(db.Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
    featured_image_id = db.Column(UUID(as_uuid=True), db.ForeignKey('media.id'))
    
    # SEO fields
    meta_title = db.Column(db.String(60))  # Recommended max length for SEO
    meta_description = db.Column(db.String(160))  # Recommended max length for SEO
    meta_keywords = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # Moderation fields
    created_by = db.Column(db.String(100))  # User ID from auth service
    updated_by = db.Column(db.String(100))  # User ID from auth service
    moderated_by = db.Column(db.String(100))  # Moderator ID from auth service
    moderation_notes = db.Column(db.Text)
    
    # Search vector for full-text search
    search_vector = db.Column(TSVECTOR)
    
    # Relationships
    featured_image = db.relationship('Media', foreign_keys=[featured_image_id])
    tags = db.relationship('Tag', secondary=page_tags, back_populates='pages')
    versions = db.relationship('ContentVersion', back_populates='content_page', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_page_status', 'status'),
        Index('idx_page_published_at', 'published_at'),
        Index('idx_page_search_vector', 'search_vector', postgresql_using='gin'),
    )

    def __repr__(self):
        return f'<ContentPage {self.slug}>'
    
    def to_dict(self, include_content=True, include_tags=False):
        """Convert the ContentPage object to a dictionary for JSON serialization."""
        result = {
            'id': self.id,
            'slug': self.slug,
            'title': self.title,
            'excerpt': self.excerpt,
            'status': self.status.value,
            'featured_image_id': str(self.featured_image_id) if self.featured_image_id else None,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'meta_keywords': self.meta_keywords,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'moderated_by': self.moderated_by,
            'moderation_notes': self.moderation_notes
        }
        
        if include_content:
            result['content'] = self.content
        
        if include_tags:
            result['tags'] = [tag.to_dict() for tag in self.tags if tag.is_active]
        
        if self.featured_image:
            result['featured_image'] = self.featured_image.to_dict()
        
        return result
    
    def update_content(self, title=None, content=None, excerpt=None, updated_by=None, **kwargs):
        """Update the content page with new information and create a version."""
        # Create version before updating
        self.create_version()
        
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if excerpt is not None:
            self.excerpt = excerpt
        if updated_by is not None:
            self.updated_by = updated_by
        
        # Update SEO fields if provided
        for field in ['meta_title', 'meta_description', 'meta_keywords']:
            if field in kwargs and kwargs[field] is not None:
                setattr(self, field, kwargs[field])
        
        self.updated_at = datetime.utcnow()
        self.update_search_vector()
    
    def publish(self, published_by=None):
        """Publish the content page."""
        self.status = ContentStatus.PUBLISHED
        self.published_at = datetime.utcnow()
        if published_by:
            self.moderated_by = published_by
    
    def archive(self, archived_by=None):
        """Archive the content page."""
        self.status = ContentStatus.ARCHIVED
        if archived_by:
            self.updated_by = archived_by
            self.updated_at = datetime.utcnow()
    
    def create_version(self):
        """Create a version snapshot of the current content."""
        version = ContentVersion(
            content_page_id=self.id,
            title=self.title,
            content=self.content,
            excerpt=self.excerpt,
            meta_title=self.meta_title,
            meta_description=self.meta_description,
            meta_keywords=self.meta_keywords,
            created_by=self.updated_by or self.created_by
        )
        db.session.add(version)
        return version
    
    def update_search_vector(self):
        """Update the search vector for full-text search."""
        if db.engine.dialect.name == 'postgresql':
            search_content = f"{self.title} {self.content} {self.excerpt or ''} {self.meta_description or ''}"
            self.search_vector = db.func.to_tsvector('english', search_content)

class Article(db.Model):
    """
    Represents a dynamic article or blog post in the system.
    
    Enhanced Article model with comprehensive content management features including
    categorization, tagging, SEO optimization, moderation workflow, and versioning.
    
    Attributes:
        id (int): The primary key identifier for the article.
        title (str): The title of the article.
        slug (str): URL-friendly identifier for the article.
        content (str): The main content of the article.
        excerpt (str): Short summary or excerpt of the article.
        author (str): The name of the article author.
        status (ContentStatus): Current status in the moderation workflow.
        featured_image_id (UUID): Reference to featured image in Media table.
        
        # SEO fields
        meta_title (str): SEO meta title.
        meta_description (str): SEO meta description.
        meta_keywords (str): SEO meta keywords.
        
        # Timestamps
        created_at (datetime): When the article was created.
        updated_at (datetime): When the article was last modified.
        published_at (datetime): When the article was published.
        
        # Moderation fields
        created_by (str): ID of the user who created the article.
        updated_by (str): ID of the user who last updated the article.
        moderated_by (str): ID of the moderator who reviewed the article.
        moderation_notes (str): Notes from the moderation process.
        
        # Engagement metrics
        view_count (int): Number of times the article has been viewed.
        like_count (int): Number of likes the article has received.
        
        # Search and indexing
        search_vector (TSVECTOR): Full-text search vector for PostgreSQL.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    author = db.Column(db.String(100))
    status = db.Column(db.Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
    featured_image_id = db.Column(UUID(as_uuid=True), db.ForeignKey('media.id'))
    
    # SEO fields
    meta_title = db.Column(db.String(60))
    meta_description = db.Column(db.String(160))
    meta_keywords = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # Moderation fields
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    moderated_by = db.Column(db.String(100))
    moderation_notes = db.Column(db.Text)
    
    # Engagement metrics
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    
    # Search vector for full-text search
    search_vector = db.Column(TSVECTOR)
    
    # Relationships
    featured_image = db.relationship('Media', foreign_keys=[featured_image_id])
    categories = db.relationship('Category', secondary=article_categories, back_populates='articles')
    tags = db.relationship('Tag', secondary=article_tags, back_populates='articles')
    versions = db.relationship('ContentVersion', back_populates='article', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_article_status', 'status'),
        Index('idx_article_published_at', 'published_at'),
        Index('idx_article_author', 'author'),
        Index('idx_article_search_vector', 'search_vector', postgresql_using='gin'),
    )

    def __repr__(self):
        return f'<Article {self.title}>'
    
    def to_dict(self, include_content=True, include_categories=False, include_tags=False):
        """Convert the Article object to a dictionary for JSON serialization."""
        result = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt,
            'author': self.author,
            'status': self.status.value,
            'featured_image_id': str(self.featured_image_id) if self.featured_image_id else None,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'meta_keywords': self.meta_keywords,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'moderated_by': self.moderated_by,
            'moderation_notes': self.moderation_notes,
            'view_count': self.view_count,
            'like_count': self.like_count
        }
        
        if include_content:
            result['content'] = self.content
        
        if include_categories:
            result['categories'] = [cat.to_dict() for cat in self.categories if cat.is_active]
        
        if include_tags:
            result['tags'] = [tag.to_dict() for tag in self.tags if tag.is_active]
        
        if self.featured_image:
            result['featured_image'] = self.featured_image.to_dict()
        
        return result
    
    def update_article(self, title=None, content=None, excerpt=None, author=None, updated_by=None, **kwargs):
        """Update the article with new information and create a version."""
        # Create version before updating
        self.create_version()
        
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if excerpt is not None:
            self.excerpt = excerpt
        if author is not None:
            self.author = author
        if updated_by is not None:
            self.updated_by = updated_by
        
        # Update SEO fields if provided
        for field in ['meta_title', 'meta_description', 'meta_keywords']:
            if field in kwargs and kwargs[field] is not None:
                setattr(self, field, kwargs[field])
        
        self.updated_at = datetime.utcnow()
        self.update_search_vector()
    
    def publish(self, published_by=None):
        """Publish the article."""
        self.status = ContentStatus.PUBLISHED
        self.published_at = datetime.utcnow()
        if published_by:
            self.moderated_by = published_by
    
    def archive(self, archived_by=None):
        """Archive the article."""
        self.status = ContentStatus.ARCHIVED
        if archived_by:
            self.updated_by = archived_by
            self.updated_at = datetime.utcnow()
    
    def increment_view_count(self):
        """Increment the view count for the article."""
        self.view_count += 1
    
    def increment_like_count(self):
        """Increment the like count for the article."""
        self.like_count += 1
    
    def create_version(self):
        """Create a version snapshot of the current content."""
        version = ContentVersion(
            article_id=self.id,
            title=self.title,
            content=self.content,
            excerpt=self.excerpt,
            meta_title=self.meta_title,
            meta_description=self.meta_description,
            meta_keywords=self.meta_keywords,
            created_by=self.updated_by or self.created_by
        )
        db.session.add(version)
        return version
    
    def update_search_vector(self):
        """Update the search vector for full-text search."""
        if db.engine.dialect.name == 'postgresql':
            search_content = f"{self.title} {self.content} {self.excerpt or ''} {self.author or ''} {self.meta_description or ''}"
            self.search_vector = db.func.to_tsvector('english', search_content)
    
    @classmethod
    def get_recent_articles(cls, limit=10, status=ContentStatus.PUBLISHED):
        """Get the most recently published articles."""
        return cls.query.filter_by(status=status).order_by(cls.published_at.desc()).limit(limit).all()
    
    @classmethod
    def get_articles_by_author(cls, author_name, status=ContentStatus.PUBLISHED):
        """Get all articles by a specific author."""
        return cls.query.filter_by(author=author_name, status=status).order_by(cls.published_at.desc()).all()
    
    @classmethod
    def get_articles_by_category(cls, category_id, status=ContentStatus.PUBLISHED):
        """Get all articles in a specific category."""
        return cls.query.join(article_categories).filter(
            article_categories.c.category_id == category_id,
            cls.status == status
        ).order_by(cls.published_at.desc()).all()
    
    @classmethod
    def get_popular_articles(cls, limit=10, status=ContentStatus.PUBLISHED):
        """Get the most popular articles by view count."""
        return cls.query.filter_by(status=status).order_by(cls.view_count.desc()).limit(limit).all()

class ContentVersion(db.Model):
    """
    Represents a historical version of content for versioning and rollback capabilities.
    
    This model stores snapshots of content at different points in time, allowing
    for version history tracking and the ability to rollback to previous versions.
    
    Attributes:
        id (int): Primary key identifier.
        content_page_id (int): Reference to ContentPage (if this is a page version).
        article_id (int): Reference to Article (if this is an article version).
        version_number (int): Sequential version number.
        title (str): Title at the time of this version.
        content (str): Content at the time of this version.
        excerpt (str): Excerpt at the time of this version.
        meta_title (str): Meta title at the time of this version.
        meta_description (str): Meta description at the time of this version.
        meta_keywords (str): Meta keywords at the time of this version.
        created_at (datetime): When this version was created.
        created_by (str): ID of the user who created this version.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    content_page_id = db.Column(db.Integer, db.ForeignKey('content_page.id'))
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
    version_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    meta_title = db.Column(db.String(60))
    meta_description = db.Column(db.String(160))
    meta_keywords = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    
    # Relationships
    content_page = db.relationship('ContentPage', back_populates='versions')
    article = db.relationship('Article', back_populates='versions')
    
    def __repr__(self):
        content_type = "Page" if self.content_page_id else "Article"
        content_id = self.content_page_id or self.article_id
        return f'<ContentVersion {content_type}:{content_id} v{self.version_number}>'
    
    def to_dict(self):
        """Convert version to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'content_page_id': self.content_page_id,
            'article_id': self.article_id,
            'version_number': self.version_number,
            'title': self.title,
            'content': self.content,
            'excerpt': self.excerpt,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'meta_keywords': self.meta_keywords,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }
    
    @classmethod
    def get_next_version_number(cls, content_page_id=None, article_id=None):
        """Get the next version number for a piece of content."""
        if content_page_id:
            last_version = cls.query.filter_by(content_page_id=content_page_id).order_by(cls.version_number.desc()).first()
        elif article_id:
            last_version = cls.query.filter_by(article_id=article_id).order_by(cls.version_number.desc()).first()
        else:
            return 1
        
        return (last_version.version_number + 1) if last_version else 1

# Event listeners for automatic version numbering
@db.event.listens_for(ContentVersion, 'before_insert')
def set_version_number(mapper, connection, target):
    """Automatically set version number before inserting a new version."""
    if target.version_number is None:
        target.version_number = ContentVersion.get_next_version_number(
            content_page_id=target.content_page_id,
            article_id=target.article_id
        )

# Event listeners for automatic search vector updates
@db.event.listens_for(ContentPage, 'before_insert')
@db.event.listens_for(ContentPage, 'before_update')
def update_page_search_vector(mapper, connection, target):
    """Automatically update search vector for content pages."""
    target.update_search_vector()

@db.event.listens_for(Article, 'before_insert')
@db.event.listens_for(Article, 'before_update')
def update_article_search_vector(mapper, connection, target):
    """Automatically update search vector for articles."""
    target.update_search_vector()
