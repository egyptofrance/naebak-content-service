"""
Content Service Data Models - Naebak Project

This module defines the database models for the Naebak Content Service.
It includes models for managing static content pages and dynamic articles
that are used throughout the Naebak platform.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ContentPage(db.Model):
    """
    Represents a static content page in the system.
    
    ContentPage is used for managing static content such as "About Us", "Terms of Service",
    "Privacy Policy", and other informational pages that don't change frequently.
    Each page is identified by a unique slug for URL-friendly access.
    
    Attributes:
        id (int): The primary key identifier for the content page.
        slug (str): A unique, URL-friendly identifier for the page (e.g., 'about-us', 'privacy-policy').
        title (str): The display title of the content page.
        content (str): The main content of the page, stored as HTML or markdown.
        last_updated (datetime): Timestamp of when the page was last modified.
    
    Business Rules:
        - Slug must be unique across all content pages
        - Slug should be URL-friendly (lowercase, hyphens instead of spaces)
        - Content can contain HTML markup for rich formatting
        - last_updated is automatically set when the page is modified
    """
    
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'about-us'
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        """
        String representation of the ContentPage object.
        
        Returns:
            str: A string representation showing the page slug.
        """
        return f'<ContentPage {self.slug}>'
    
    def to_dict(self):
        """
        Convert the ContentPage object to a dictionary for JSON serialization.
        
        Returns:
            dict: A dictionary representation of the content page.
        """
        return {
            'id': self.id,
            'slug': self.slug,
            'title': self.title,
            'content': self.content,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def update_content(self, title=None, content=None):
        """
        Update the content page with new information.
        
        This method updates the page content and automatically sets the last_updated timestamp.
        
        Args:
            title (str, optional): New title for the page.
            content (str, optional): New content for the page.
        """
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        self.last_updated = datetime.utcnow()

class Article(db.Model):
    """
    Represents a dynamic article or blog post in the system.
    
    Article is used for managing dynamic content such as blog posts, news articles,
    announcements, and other time-sensitive content that is published regularly.
    Articles support authorship attribution and are ordered by publication date.
    
    Attributes:
        id (int): The primary key identifier for the article.
        title (str): The title of the article.
        content (str): The main content of the article, stored as HTML or markdown.
        author (str): The name of the article author (optional).
        publish_date (datetime): When the article was published.
    
    Business Rules:
        - Articles are ordered by publish_date in descending order (newest first)
        - Author field is optional to support anonymous or system-generated content
        - Content can contain HTML markup for rich formatting
        - publish_date is automatically set when the article is created
    """
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=True)
    publish_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        """
        String representation of the Article object.
        
        Returns:
            str: A string representation showing the article title.
        """
        return f'<Article {self.title}>'
    
    def to_dict(self):
        """
        Convert the Article object to a dictionary for JSON serialization.
        
        Returns:
            dict: A dictionary representation of the article.
        """
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None
        }
    
    def update_article(self, title=None, content=None, author=None):
        """
        Update the article with new information.
        
        This method allows updating article fields while preserving the original
        publish_date to maintain chronological ordering.
        
        Args:
            title (str, optional): New title for the article.
            content (str, optional): New content for the article.
            author (str, optional): New author for the article.
        """
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if author is not None:
            self.author = author
    
    @classmethod
    def get_recent_articles(cls, limit=10):
        """
        Get the most recently published articles.
        
        This class method provides a convenient way to retrieve the latest articles
        for display on the homepage or in article listings.
        
        Args:
            limit (int): Maximum number of articles to return (default: 10).
            
        Returns:
            list: A list of Article objects ordered by publish_date (newest first).
        """
        return cls.query.order_by(cls.publish_date.desc()).limit(limit).all()
    
    @classmethod
    def get_articles_by_author(cls, author_name):
        """
        Get all articles by a specific author.
        
        Args:
            author_name (str): The name of the author to search for.
            
        Returns:
            list: A list of Article objects by the specified author.
        """
        return cls.query.filter_by(author=author_name).order_by(cls.publish_date.desc()).all()
