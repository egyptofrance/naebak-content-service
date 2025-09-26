"""
Advanced Search and SEO Optimization System for Naebak Content Service

This module provides comprehensive search capabilities and SEO optimization
for all content types in the Naebak platform.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import re
import json
from dataclasses import dataclass
from urllib.parse import quote
import hashlib

from flask import current_app, request
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import aliased
from models import db, Content, Category, Tag, ContentTag


@dataclass
class SearchResult:
    """Search result data structure"""
    content_id: int
    title: str
    excerpt: str
    content_type: str
    author_name: str
    published_at: datetime
    relevance_score: float
    highlighted_text: str
    url: str
    tags: List[str]
    category: str


@dataclass
class SEOMetadata:
    """SEO metadata structure"""
    title: str
    description: str
    keywords: List[str]
    canonical_url: str
    og_title: str
    og_description: str
    og_image: str
    twitter_title: str
    twitter_description: str
    schema_markup: Dict[str, Any]


class AdvancedSearchEngine:
    """
    Advanced search engine with full-text search, filtering, and ranking capabilities.
    
    Features:
    - Full-text search with Arabic support
    - Advanced filtering and faceting
    - Relevance scoring and ranking
    - Search suggestions and autocomplete
    - Search analytics and optimization
    """
    
    def __init__(self):
        self.min_search_length = 2
        self.max_results_per_page = 50
        self.default_results_per_page = 20
        self.search_cache_ttl = 300  # 5 minutes
    
    def search(self, query: str, filters: Dict[str, Any] = None, 
               page: int = 1, per_page: int = None) -> Dict[str, Any]:
        """
        Perform advanced content search
        
        Args:
            query: Search query string
            filters: Additional filters (category, tags, date_range, etc.)
            page: Page number for pagination
            per_page: Results per page
            
        Returns:
            Search results with metadata
        """
        try:
            # Validate and clean query
            cleaned_query = self._clean_search_query(query)
            if len(cleaned_query) < self.min_search_length:
                return {"error": "Query too short", "min_length": self.min_search_length}
            
            # Set pagination
            per_page = per_page or self.default_results_per_page
            per_page = min(per_page, self.max_results_per_page)
            offset = (page - 1) * per_page
            
            # Build search query
            search_query = self._build_search_query(cleaned_query, filters)
            
            # Execute search with pagination
            results = search_query.offset(offset).limit(per_page).all()
            total_count = search_query.count()
            
            # Process and rank results
            processed_results = self._process_search_results(results, cleaned_query)
            
            # Generate search suggestions
            suggestions = self._generate_search_suggestions(cleaned_query, total_count)
            
            # Log search for analytics
            self._log_search(cleaned_query, filters, total_count)
            
            return {
                "query": query,
                "cleaned_query": cleaned_query,
                "results": processed_results,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "pages": (total_count + per_page - 1) // per_page
                },
                "suggestions": suggestions,
                "filters_applied": filters or {},
                "search_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"Search error: {str(e)}")
            return {"error": "Search failed"}
    
    def _clean_search_query(self, query: str) -> str:
        """Clean and normalize search query"""
        if not query:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', query.strip())
        
        # Remove special characters that might break search
        cleaned = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', ' ', cleaned)
        
        # Normalize Arabic text (basic normalization)
        arabic_normalizations = {
            'أ': 'ا', 'إ': 'ا', 'آ': 'ا',
            'ة': 'ه',
            'ى': 'ي'
        }
        
        for old, new in arabic_normalizations.items():
            cleaned = cleaned.replace(old, new)
        
        return cleaned.strip()
    
    def _build_search_query(self, query: str, filters: Dict[str, Any] = None):
        """Build SQLAlchemy search query with filters"""
        # Start with base query
        search_query = db.session.query(Content).filter(
            Content.status == 'published',
            Content.moderation_status == 'approved'
        )
        
        # Add full-text search
        if query:
            # Create search conditions for different fields with weights
            title_match = Content.title.ilike(f'%{query}%')
            body_match = Content.body.ilike(f'%{query}%')
            
            # Combine with OR and add to query
            search_query = search_query.filter(
                or_(title_match, body_match)
            )
        
        # Apply filters
        if filters:
            search_query = self._apply_search_filters(search_query, filters)
        
        # Order by relevance (simplified scoring)
        search_query = search_query.order_by(
            Content.updated_at.desc(),
            Content.view_count.desc()
        )
        
        return search_query
    
    def _apply_search_filters(self, query, filters: Dict[str, Any]):
        """Apply various filters to search query"""
        
        # Category filter
        if 'category' in filters and filters['category']:
            if isinstance(filters['category'], list):
                query = query.filter(Content.category_id.in_(filters['category']))
            else:
                query = query.filter(Content.category_id == filters['category'])
        
        # Tags filter
        if 'tags' in filters and filters['tags']:
            tag_ids = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            query = query.join(ContentTag).filter(ContentTag.tag_id.in_(tag_ids))
        
        # Content type filter
        if 'content_type' in filters and filters['content_type']:
            query = query.filter(Content.content_type == filters['content_type'])
        
        # Author filter
        if 'author' in filters and filters['author']:
            query = query.filter(Content.author_id == filters['author'])
        
        # Date range filter
        if 'date_from' in filters and filters['date_from']:
            query = query.filter(Content.published_at >= filters['date_from'])
        
        if 'date_to' in filters and filters['date_to']:
            query = query.filter(Content.published_at <= filters['date_to'])
        
        # Language filter
        if 'language' in filters and filters['language']:
            query = query.filter(Content.language == filters['language'])
        
        # Status filter (for admin searches)
        if 'status' in filters and filters['status']:
            query = query.filter(Content.status == filters['status'])
        
        return query
    
    def _process_search_results(self, results: List[Content], query: str) -> List[Dict[str, Any]]:
        """Process and enhance search results"""
        processed_results = []
        
        for content in results:
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(content, query)
            
            # Generate excerpt with highlighting
            excerpt, highlighted = self._generate_excerpt_with_highlighting(content.body, query)
            
            # Get tags
            tags = [tag.name for tag in content.tags] if content.tags else []
            
            # Get category name
            category_name = content.category.name if content.category else ""
            
            result = {
                "id": content.id,
                "title": content.title,
                "excerpt": excerpt,
                "highlighted_excerpt": highlighted,
                "content_type": content.content_type,
                "author_name": content.author_name,
                "published_at": content.published_at.isoformat() if content.published_at else None,
                "updated_at": content.updated_at.isoformat(),
                "relevance_score": relevance_score,
                "url": f"/content/{content.id}",
                "tags": tags,
                "category": category_name,
                "view_count": content.view_count or 0,
                "featured_image": content.featured_image
            }
            
            processed_results.append(result)
        
        # Sort by relevance score
        processed_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return processed_results
    
    def _calculate_relevance_score(self, content: Content, query: str) -> float:
        """Calculate relevance score for search result"""
        score = 0.0
        query_lower = query.lower()
        
        # Title match (highest weight)
        if query_lower in content.title.lower():
            score += 10.0
            # Exact title match gets bonus
            if query_lower == content.title.lower():
                score += 5.0
        
        # Body content match
        body_lower = content.body.lower()
        query_count = body_lower.count(query_lower)
        score += query_count * 2.0
        
        # Recency bonus (newer content gets slight boost)
        if content.published_at:
            days_old = (datetime.utcnow() - content.published_at).days
            if days_old < 7:
                score += 2.0
            elif days_old < 30:
                score += 1.0
        
        # Popularity bonus
        if content.view_count:
            score += min(content.view_count * 0.01, 5.0)
        
        # Content type bonus
        if content.content_type in ['news', 'announcement']:
            score += 1.0
        
        return round(score, 2)
    
    def _generate_excerpt_with_highlighting(self, text: str, query: str, 
                                          excerpt_length: int = 200) -> Tuple[str, str]:
        """Generate excerpt with query highlighting"""
        if not text or not query:
            excerpt = text[:excerpt_length] + "..." if len(text) > excerpt_length else text
            return excerpt, excerpt
        
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Find first occurrence of query
        query_pos = text_lower.find(query_lower)
        
        if query_pos == -1:
            # Query not found, return beginning of text
            excerpt = text[:excerpt_length] + "..." if len(text) > excerpt_length else text
            return excerpt, excerpt
        
        # Calculate excerpt boundaries
        start_pos = max(0, query_pos - excerpt_length // 3)
        end_pos = min(len(text), start_pos + excerpt_length)
        
        # Adjust to word boundaries
        if start_pos > 0:
            start_pos = text.find(' ', start_pos) + 1
        if end_pos < len(text):
            end_pos = text.rfind(' ', start_pos, end_pos)
        
        excerpt = text[start_pos:end_pos]
        if start_pos > 0:
            excerpt = "..." + excerpt
        if end_pos < len(text):
            excerpt = excerpt + "..."
        
        # Create highlighted version
        highlighted = re.sub(
            f'({re.escape(query)})',
            r'<mark>\1</mark>',
            excerpt,
            flags=re.IGNORECASE
        )
        
        return excerpt, highlighted
    
    def _generate_search_suggestions(self, query: str, result_count: int) -> List[str]:
        """Generate search suggestions based on query and results"""
        suggestions = []
        
        if result_count == 0:
            # No results - suggest alternatives
            suggestions.extend(self._get_alternative_suggestions(query))
        elif result_count < 5:
            # Few results - suggest broader terms
            suggestions.extend(self._get_broader_suggestions(query))
        
        # Add popular search terms
        suggestions.extend(self._get_popular_search_terms())
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _get_alternative_suggestions(self, query: str) -> List[str]:
        """Get alternative search suggestions for failed searches"""
        # Simple implementation - in production, use more sophisticated methods
        alternatives = []
        
        # Remove last word and suggest
        words = query.split()
        if len(words) > 1:
            alternatives.append(' '.join(words[:-1]))
        
        # Common alternative spellings for Arabic
        arabic_alternatives = {
            'الحكومة': ['الحكومه', 'حكومة'],
            'البرلمان': ['برلمان', 'المجلس'],
            'النائب': ['نائب', 'النواب']
        }
        
        for original, alts in arabic_alternatives.items():
            if original in query:
                for alt in alts:
                    alternatives.append(query.replace(original, alt))
        
        return alternatives[:3]
    
    def _get_broader_suggestions(self, query: str) -> List[str]:
        """Get broader search suggestions"""
        broader_terms = {
            'نائب': 'نواب',
            'قانون': 'قوانين',
            'مشروع': 'مشاريع',
            'جلسة': 'جلسات'
        }
        
        suggestions = []
        for narrow, broad in broader_terms.items():
            if narrow in query:
                suggestions.append(query.replace(narrow, broad))
        
        return suggestions
    
    def _get_popular_search_terms(self) -> List[str]:
        """Get popular search terms from analytics"""
        # In production, this would query search analytics
        return [
            'أخبار البرلمان',
            'قوانين جديدة',
            'جلسات النواب',
            'مشاريع القوانين'
        ]
    
    def _log_search(self, query: str, filters: Dict[str, Any], result_count: int):
        """Log search for analytics (simplified implementation)"""
        try:
            # In production, this would log to analytics system
            current_app.logger.info(
                f"Search: query='{query}', filters={filters}, results={result_count}"
            )
        except Exception as e:
            current_app.logger.error(f"Search logging error: {str(e)}")
    
    def get_search_autocomplete(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions for partial queries"""
        if len(partial_query) < 2:
            return []
        
        # Search in content titles and popular terms
        title_matches = db.session.query(Content.title).filter(
            and_(
                Content.title.ilike(f'%{partial_query}%'),
                Content.status == 'published'
            )
        ).limit(limit).all()
        
        suggestions = [match[0] for match in title_matches]
        
        # Add popular terms that match
        popular_terms = self._get_popular_search_terms()
        for term in popular_terms:
            if partial_query.lower() in term.lower() and term not in suggestions:
                suggestions.append(term)
        
        return suggestions[:limit]
    
    def get_search_facets(self, query: str = "", filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get search facets for filtering"""
        base_query = self._build_search_query(query, filters)
        
        # Category facets
        category_facets = db.session.query(
            Category.id,
            Category.name,
            func.count(Content.id).label('count')
        ).join(Content).filter(
            Content.id.in_(base_query.subquery())
        ).group_by(Category.id, Category.name).all()
        
        # Content type facets
        type_facets = base_query.with_entities(
            Content.content_type,
            func.count(Content.id).label('count')
        ).group_by(Content.content_type).all()
        
        # Date range facets
        date_facets = self._get_date_range_facets(base_query)
        
        return {
            "categories": [
                {"id": cat[0], "name": cat[1], "count": cat[2]}
                for cat in category_facets
            ],
            "content_types": [
                {"type": type_facet[0], "count": type_facet[1]}
                for type_facet in type_facets
            ],
            "date_ranges": date_facets
        }
    
    def _get_date_range_facets(self, base_query) -> List[Dict[str, Any]]:
        """Get date range facets"""
        now = datetime.utcnow()
        ranges = [
            ("last_week", now - timedelta(days=7)),
            ("last_month", now - timedelta(days=30)),
            ("last_3_months", now - timedelta(days=90)),
            ("last_year", now - timedelta(days=365))
        ]
        
        facets = []
        for range_name, start_date in ranges:
            count = base_query.filter(Content.published_at >= start_date).count()
            facets.append({
                "range": range_name,
                "start_date": start_date.isoformat(),
                "count": count
            })
        
        return facets


class SEOOptimizationEngine:
    """
    Advanced SEO optimization engine for content.
    
    Features:
    - Automatic meta tag generation
    - Schema.org markup
    - Open Graph and Twitter Cards
    - SEO analysis and recommendations
    - Sitemap generation
    """
    
    def __init__(self):
        self.default_description_length = 160
        self.default_title_length = 60
        self.base_url = current_app.config.get('BASE_URL', 'https://naebak.gov.eg')
    
    def generate_seo_metadata(self, content: Content) -> SEOMetadata:
        """Generate comprehensive SEO metadata for content"""
        try:
            # Generate optimized title
            seo_title = self._generate_seo_title(content)
            
            # Generate meta description
            meta_description = self._generate_meta_description(content)
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            # Generate URLs
            canonical_url = f"{self.base_url}/content/{content.id}"
            
            # Generate Open Graph metadata
            og_title = seo_title
            og_description = meta_description
            og_image = content.featured_image or f"{self.base_url}/static/default-og-image.jpg"
            
            # Generate Twitter Card metadata
            twitter_title = seo_title
            twitter_description = meta_description
            
            # Generate Schema.org markup
            schema_markup = self._generate_schema_markup(content)
            
            return SEOMetadata(
                title=seo_title,
                description=meta_description,
                keywords=keywords,
                canonical_url=canonical_url,
                og_title=og_title,
                og_description=og_description,
                og_image=og_image,
                twitter_title=twitter_title,
                twitter_description=twitter_description,
                schema_markup=schema_markup
            )
            
        except Exception as e:
            current_app.logger.error(f"SEO metadata generation error: {str(e)}")
            return self._get_default_seo_metadata(content)
    
    def _generate_seo_title(self, content: Content) -> str:
        """Generate SEO-optimized title"""
        title = content.title
        
        # Add site name if title is short
        if len(title) < 40:
            title += " | منصة نائبك"
        
        # Truncate if too long
        if len(title) > self.default_title_length:
            title = title[:self.default_title_length - 3] + "..."
        
        return title
    
    def _generate_meta_description(self, content: Content) -> str:
        """Generate meta description from content"""
        if content.excerpt:
            description = content.excerpt
        else:
            # Extract from body content
            clean_body = re.sub(r'<[^>]+>', '', content.body)  # Remove HTML
            description = clean_body[:self.default_description_length]
        
        # Ensure proper length
        if len(description) > self.default_description_length:
            description = description[:self.default_description_length - 3] + "..."
        
        return description.strip()
    
    def _extract_keywords(self, content: Content) -> List[str]:
        """Extract SEO keywords from content"""
        keywords = []
        
        # Add tags as keywords
        if content.tags:
            keywords.extend([tag.name for tag in content.tags])
        
        # Add category as keyword
        if content.category:
            keywords.append(content.category.name)
        
        # Extract keywords from title and body (simplified)
        text = f"{content.title} {content.body}".lower()
        
        # Common Arabic political keywords
        political_keywords = [
            'برلمان', 'نائب', 'قانون', 'مشروع', 'جلسة', 'تصويت',
            'حكومة', 'وزير', 'مجلس', 'لجنة', 'مناقشة', 'قرار'
        ]
        
        for keyword in political_keywords:
            if keyword in text and keyword not in keywords:
                keywords.append(keyword)
        
        return keywords[:10]  # Limit to 10 keywords
    
    def _generate_schema_markup(self, content: Content) -> Dict[str, Any]:
        """Generate Schema.org structured data markup"""
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": content.title,
            "description": self._generate_meta_description(content),
            "url": f"{self.base_url}/content/{content.id}",
            "datePublished": content.published_at.isoformat() if content.published_at else None,
            "dateModified": content.updated_at.isoformat(),
            "author": {
                "@type": "Person",
                "name": content.author_name
            },
            "publisher": {
                "@type": "Organization",
                "name": "منصة نائبك",
                "url": self.base_url,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{self.base_url}/static/logo.png"
                }
            }
        }
        
        # Add image if available
        if content.featured_image:
            schema["image"] = {
                "@type": "ImageObject",
                "url": content.featured_image
            }
        
        # Add category/section
        if content.category:
            schema["articleSection"] = content.category.name
        
        # Add keywords
        keywords = self._extract_keywords(content)
        if keywords:
            schema["keywords"] = keywords
        
        return schema
    
    def _get_default_seo_metadata(self, content: Content) -> SEOMetadata:
        """Get default SEO metadata as fallback"""
        return SEOMetadata(
            title=content.title + " | منصة نائبك",
            description="اطلع على آخر أخبار البرلمان والنواب في منصة نائبك",
            keywords=["برلمان", "نواب", "سياسة"],
            canonical_url=f"{self.base_url}/content/{content.id}",
            og_title=content.title,
            og_description="منصة نائبك - تابع أخبار البرلمان",
            og_image=f"{self.base_url}/static/default-og-image.jpg",
            twitter_title=content.title,
            twitter_description="منصة نائبك - تابع أخبار البرلمان",
            schema_markup={}
        )
    
    def analyze_seo_score(self, content: Content) -> Dict[str, Any]:
        """Analyze SEO score and provide recommendations"""
        score = 0
        max_score = 100
        recommendations = []
        
        # Title analysis (20 points)
        title_score = self._analyze_title_seo(content.title, recommendations)
        score += title_score
        
        # Content length analysis (15 points)
        content_score = self._analyze_content_length(content.body, recommendations)
        score += content_score
        
        # Meta description analysis (15 points)
        desc_score = self._analyze_meta_description(content, recommendations)
        score += desc_score
        
        # Keywords analysis (20 points)
        keyword_score = self._analyze_keywords(content, recommendations)
        score += keyword_score
        
        # Images analysis (10 points)
        image_score = self._analyze_images(content, recommendations)
        score += image_score
        
        # Internal links analysis (10 points)
        link_score = self._analyze_internal_links(content.body, recommendations)
        score += link_score
        
        # Readability analysis (10 points)
        readability_score = self._analyze_readability(content.body, recommendations)
        score += readability_score
        
        # Determine overall grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": score,
            "max_score": max_score,
            "grade": grade,
            "recommendations": recommendations,
            "breakdown": {
                "title": title_score,
                "content_length": content_score,
                "meta_description": desc_score,
                "keywords": keyword_score,
                "images": image_score,
                "internal_links": link_score,
                "readability": readability_score
            }
        }
    
    def _analyze_title_seo(self, title: str, recommendations: List[str]) -> int:
        """Analyze title for SEO (max 20 points)"""
        score = 0
        
        if not title:
            recommendations.append("إضافة عنوان للمحتوى")
            return 0
        
        # Length check
        if 30 <= len(title) <= 60:
            score += 10
        elif len(title) < 30:
            recommendations.append("العنوان قصير جداً - يفضل 30-60 حرف")
            score += 5
        else:
            recommendations.append("العنوان طويل جداً - يفضل 30-60 حرف")
            score += 5
        
        # Keyword presence (simplified)
        political_keywords = ['برلمان', 'نائب', 'قانون', 'مجلس']
        if any(keyword in title.lower() for keyword in political_keywords):
            score += 10
        else:
            recommendations.append("إضافة كلمات مفتاحية مهمة في العنوان")
        
        return score
    
    def _analyze_content_length(self, body: str, recommendations: List[str]) -> int:
        """Analyze content length (max 15 points)"""
        if not body:
            recommendations.append("إضافة محتوى للمقال")
            return 0
        
        word_count = len(body.split())
        
        if word_count >= 300:
            return 15
        elif word_count >= 150:
            recommendations.append("زيادة طول المحتوى - يفضل 300 كلمة على الأقل")
            return 10
        else:
            recommendations.append("المحتوى قصير جداً - يفضل 300 كلمة على الأقل")
            return 5
    
    def _analyze_meta_description(self, content: Content, recommendations: List[str]) -> int:
        """Analyze meta description (max 15 points)"""
        description = content.excerpt or ""
        
        if not description:
            recommendations.append("إضافة وصف مختصر للمحتوى")
            return 0
        
        if 120 <= len(description) <= 160:
            return 15
        elif len(description) < 120:
            recommendations.append("الوصف قصير - يفضل 120-160 حرف")
            return 10
        else:
            recommendations.append("الوصف طويل - يفضل 120-160 حرف")
            return 10
    
    def _analyze_keywords(self, content: Content, recommendations: List[str]) -> int:
        """Analyze keywords usage (max 20 points)"""
        score = 0
        
        # Check if content has tags
        if content.tags and len(content.tags) >= 3:
            score += 10
        else:
            recommendations.append("إضافة علامات (tags) للمحتوى")
        
        # Check keyword density in content
        text = f"{content.title} {content.body}".lower()
        political_keywords = ['برلمان', 'نائب', 'قانون', 'مجلس', 'حكومة']
        
        keyword_count = sum(1 for keyword in political_keywords if keyword in text)
        if keyword_count >= 2:
            score += 10
        else:
            recommendations.append("استخدام كلمات مفتاحية أكثر في المحتوى")
        
        return score
    
    def _analyze_images(self, content: Content, recommendations: List[str]) -> int:
        """Analyze images usage (max 10 points)"""
        if content.featured_image:
            return 10
        else:
            recommendations.append("إضافة صورة مميزة للمحتوى")
            return 0
    
    def _analyze_internal_links(self, body: str, recommendations: List[str]) -> int:
        """Analyze internal links (max 10 points)"""
        # Count internal links (simplified)
        internal_link_count = body.count('/content/') + body.count('/news/')
        
        if internal_link_count >= 2:
            return 10
        elif internal_link_count == 1:
            recommendations.append("إضافة روابط داخلية أكثر")
            return 5
        else:
            recommendations.append("إضافة روابط داخلية للمحتوى ذي الصلة")
            return 0
    
    def _analyze_readability(self, body: str, recommendations: List[str]) -> int:
        """Analyze content readability (max 10 points)"""
        if not body:
            return 0
        
        # Simple readability metrics
        sentences = body.split('.')
        words = body.split()
        
        if not sentences or not words:
            return 5
        
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Good readability: 15-20 words per sentence
        if 10 <= avg_words_per_sentence <= 25:
            return 10
        elif avg_words_per_sentence > 25:
            recommendations.append("تقسيم الجمل الطويلة لتحسين القراءة")
            return 5
        else:
            return 8
    
    def generate_sitemap_entry(self, content: Content) -> Dict[str, Any]:
        """Generate sitemap entry for content"""
        return {
            "url": f"{self.base_url}/content/{content.id}",
            "lastmod": content.updated_at.isoformat(),
            "changefreq": "weekly",
            "priority": self._calculate_sitemap_priority(content)
        }
    
    def _calculate_sitemap_priority(self, content: Content) -> float:
        """Calculate sitemap priority for content"""
        priority = 0.5  # Default priority
        
        # Boost for recent content
        if content.published_at:
            days_old = (datetime.utcnow() - content.published_at).days
            if days_old < 7:
                priority += 0.3
            elif days_old < 30:
                priority += 0.2
        
        # Boost for popular content
        if content.view_count and content.view_count > 100:
            priority += 0.2
        
        # Boost for important content types
        if content.content_type in ['news', 'announcement']:
            priority += 0.1
        
        return min(priority, 1.0)


# Initialize engines
search_engine = AdvancedSearchEngine()
seo_engine = SEOOptimizationEngine()
