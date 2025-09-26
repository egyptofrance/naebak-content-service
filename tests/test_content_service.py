"""
Comprehensive Test Suite for Naebak Content Service

This module contains comprehensive tests for all content service functionality
including content management, moderation, versioning, search, and SEO.
"""

import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask
from flask_testing import TestCase

# Import the application and models
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Content, Category, Tag, ContentTag, ContentVersion, ModerationLog
from content_moderation import ContentModerationSystem, ContentVersioningSystem
from search_seo import AdvancedSearchEngine, SEOOptimizationEngine


class ContentServiceTestCase(TestCase):
    """Base test case for content service tests"""
    
    def create_app(self):
        """Create test application"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    def setUp(self):
        """Set up test environment"""
        db.create_all()
        self.create_test_data()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
    
    def create_test_data(self):
        """Create test data for tests"""
        # Create test category
        self.test_category = Category(
            name="أخبار البرلمان",
            description="أخبار وتطورات البرلمان",
            slug="parliament-news"
        )
        db.session.add(self.test_category)
        
        # Create test tags
        self.test_tag1 = Tag(name="برلمان", slug="parliament")
        self.test_tag2 = Tag(name="قوانين", slug="laws")
        db.session.add_all([self.test_tag1, self.test_tag2])
        
        # Create test content
        self.test_content = Content(
            title="مشروع قانون جديد في البرلمان",
            body="تم مناقشة مشروع قانون جديد في جلسة البرلمان اليوم. يهدف هذا القانون إلى تحسين الخدمات العامة وتطوير البنية التحتية.",
            content_type="news",
            status="published",
            moderation_status="approved",
            author_id=1,
            author_name="محرر الأخبار",
            category_id=1,
            published_at=datetime.utcnow(),
            view_count=150,
            featured_image="https://example.com/image.jpg"
        )
        db.session.add(self.test_content)
        
        db.session.commit()
        
        # Add tags to content
        content_tag1 = ContentTag(content_id=self.test_content.id, tag_id=self.test_tag1.id)
        content_tag2 = ContentTag(content_id=self.test_content.id, tag_id=self.test_tag2.id)
        db.session.add_all([content_tag1, content_tag2])
        db.session.commit()


class TestContentManagementAPI(ContentServiceTestCase):
    """Test content management API endpoints"""
    
    def test_get_all_content(self):
        """Test getting all content"""
        response = self.client.get('/api/content')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('content', data)
        self.assertEqual(len(data['content']), 1)
        self.assertEqual(data['content'][0]['title'], "مشروع قانون جديد في البرلمان")
    
    def test_get_content_by_id(self):
        """Test getting specific content by ID"""
        response = self.client.get(f'/api/content/{self.test_content.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['title'], "مشروع قانون جديد في البرلمان")
        self.assertEqual(data['content_type'], "news")
        self.assertIn('tags', data)
        self.assertEqual(len(data['tags']), 2)
    
    def test_create_content(self):
        """Test creating new content"""
        new_content = {
            "title": "إعلان مهم من البرلمان",
            "body": "إعلان مهم حول جلسة استثنائية للبرلمان",
            "content_type": "announcement",
            "category_id": self.test_category.id,
            "author_id": 1,
            "author_name": "المحرر الرئيسي",
            "tags": [self.test_tag1.id]
        }
        
        response = self.client.post(
            '/api/content',
            data=json.dumps(new_content),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], "إعلان مهم من البرلمان")
        self.assertEqual(data['status'], "draft")
    
    def test_update_content(self):
        """Test updating existing content"""
        updated_data = {
            "title": "مشروع قانون محدث في البرلمان",
            "body": "تم تحديث مشروع القانون بعد المناقشات"
        }
        
        response = self.client.put(
            f'/api/content/{self.test_content.id}',
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], "مشروع قانون محدث في البرلمان")
    
    def test_delete_content(self):
        """Test deleting content"""
        response = self.client.delete(f'/api/content/{self.test_content.id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify content is deleted
        response = self.client.get(f'/api/content/{self.test_content.id}')
        self.assertEqual(response.status_code, 404)
    
    def test_publish_content(self):
        """Test publishing content"""
        # Create draft content
        draft_content = Content(
            title="مسودة مقال",
            body="محتوى المسودة",
            content_type="article",
            status="draft",
            author_id=1,
            author_name="كاتب"
        )
        db.session.add(draft_content)
        db.session.commit()
        
        response = self.client.post(f'/api/content/{draft_content.id}/publish')
        self.assertEqual(response.status_code, 200)
        
        # Verify content is published
        updated_content = Content.query.get(draft_content.id)
        self.assertEqual(updated_content.status, "published")
        self.assertIsNotNone(updated_content.published_at)


class TestContentModerationSystem(ContentServiceTestCase):
    """Test content moderation system"""
    
    def setUp(self):
        super().setUp()
        self.moderation_system = ContentModerationSystem()
    
    def test_moderate_clean_content(self):
        """Test moderating clean content"""
        result = self.moderation_system.moderate_content(self.test_content.id)
        
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'approved')
        self.assertIn('confidence', result)
        self.assertGreater(result['confidence'], 0.5)
    
    def test_moderate_inappropriate_content(self):
        """Test moderating inappropriate content"""
        # Create content with inappropriate language
        inappropriate_content = Content(
            title="محتوى غير لائق",
            body="هذا محتوى يحتوي على كلمات غير لائقة ولغة مسيئة",
            content_type="article",
            status="draft",
            author_id=1,
            author_name="كاتب"
        )
        db.session.add(inappropriate_content)
        db.session.commit()
        
        result = self.moderation_system.moderate_content(inappropriate_content.id)
        
        self.assertIn('triggered_rules', result)
        self.assertTrue(len(result['triggered_rules']) > 0)
        self.assertIn('needs_human_review', result)
    
    def test_moderation_queue(self):
        """Test getting moderation queue"""
        # Create content that needs review
        review_content = Content(
            title="محتوى للمراجعة",
            body="محتوى يحتاج مراجعة بشرية",
            content_type="article",
            status="draft",
            moderation_status="under_review",
            review_priority=3,
            author_id=1,
            author_name="كاتب"
        )
        db.session.add(review_content)
        db.session.commit()
        
        queue = self.moderation_system.get_moderation_queue(moderator_id=1)
        
        self.assertIsInstance(queue, list)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['title'], "محتوى للمراجعة")
    
    def test_moderation_stats(self):
        """Test getting moderation statistics"""
        stats = self.moderation_system.get_moderation_stats(days=30)
        
        self.assertIn('period_days', stats)
        self.assertIn('status_distribution', stats)
        self.assertIn('automated_decisions', stats)
        self.assertIn('manual_decisions', stats)
        self.assertEqual(stats['period_days'], 30)


class TestContentVersioningSystem(ContentServiceTestCase):
    """Test content versioning system"""
    
    def setUp(self):
        super().setUp()
        self.versioning_system = ContentVersioningSystem()
    
    def test_create_version(self):
        """Test creating content version"""
        result = self.versioning_system.create_version(
            content_id=self.test_content.id,
            user_id=1,
            version_type="manual",
            notes="نسخة تجريبية"
        )
        
        self.assertIn('version_id', result)
        self.assertIn('version_number', result)
        self.assertEqual(result['version_number'], 1)
    
    def test_version_history(self):
        """Test getting version history"""
        # Create multiple versions
        for i in range(3):
            self.versioning_system.create_version(
                content_id=self.test_content.id,
                user_id=1,
                version_type="auto",
                notes=f"نسخة {i+1}"
            )
        
        history = self.versioning_system.get_version_history(self.test_content.id)
        
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['version_number'], 3)  # Latest first
    
    def test_compare_versions(self):
        """Test comparing versions"""
        # Create first version
        version1 = self.versioning_system.create_version(
            content_id=self.test_content.id,
            user_id=1,
            version_type="manual"
        )
        
        # Update content
        self.test_content.title = "عنوان محدث"
        self.test_content.body = "محتوى محدث"
        db.session.commit()
        
        # Create second version
        version2 = self.versioning_system.create_version(
            content_id=self.test_content.id,
            user_id=1,
            version_type="manual"
        )
        
        # Compare versions
        diff = self.versioning_system.compare_versions(
            version1['version_id'],
            version2['version_id']
        )
        
        self.assertIn('title_changed', diff)
        self.assertIn('body_changed', diff)
        self.assertTrue(diff['title_changed'])
        self.assertTrue(diff['body_changed'])
    
    def test_rollback_to_version(self):
        """Test rolling back to previous version"""
        original_title = self.test_content.title
        
        # Create version
        version = self.versioning_system.create_version(
            content_id=self.test_content.id,
            user_id=1,
            version_type="manual"
        )
        
        # Update content
        self.test_content.title = "عنوان جديد"
        db.session.commit()
        
        # Rollback
        result = self.versioning_system.rollback_to_version(
            content_id=self.test_content.id,
            version_id=version['version_id'],
            user_id=1
        )
        
        self.assertTrue(result['success'])
        
        # Verify rollback
        updated_content = Content.query.get(self.test_content.id)
        self.assertEqual(updated_content.title, original_title)


class TestAdvancedSearchEngine(ContentServiceTestCase):
    """Test advanced search engine"""
    
    def setUp(self):
        super().setUp()
        self.search_engine = AdvancedSearchEngine()
    
    def test_basic_search(self):
        """Test basic content search"""
        result = self.search_engine.search("قانون")
        
        self.assertIn('results', result)
        self.assertIn('pagination', result)
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(result['results'][0]['title'], "مشروع قانون جديد في البرلمان")
    
    def test_search_with_filters(self):
        """Test search with filters"""
        filters = {
            'category': self.test_category.id,
            'content_type': 'news'
        }
        
        result = self.search_engine.search("قانون", filters=filters)
        
        self.assertIn('results', result)
        self.assertEqual(len(result['results']), 1)
        self.assertIn('filters_applied', result)
    
    def test_search_pagination(self):
        """Test search pagination"""
        # Create more test content
        for i in range(5):
            content = Content(
                title=f"مقال {i+1} عن القوانين",
                body=f"محتوى المقال {i+1}",
                content_type="article",
                status="published",
                moderation_status="approved",
                author_id=1,
                author_name="كاتب"
            )
            db.session.add(content)
        db.session.commit()
        
        result = self.search_engine.search("قانون", page=1, per_page=3)
        
        self.assertEqual(len(result['results']), 3)
        self.assertEqual(result['pagination']['page'], 1)
        self.assertEqual(result['pagination']['per_page'], 3)
        self.assertGreater(result['pagination']['total'], 3)
    
    def test_search_autocomplete(self):
        """Test search autocomplete"""
        suggestions = self.search_engine.get_search_autocomplete("قان")
        
        self.assertIsInstance(suggestions, list)
        # Should include our test content title
        matching_suggestions = [s for s in suggestions if "قانون" in s]
        self.assertGreater(len(matching_suggestions), 0)
    
    def test_search_facets(self):
        """Test search facets"""
        facets = self.search_engine.get_search_facets("قانون")
        
        self.assertIn('categories', facets)
        self.assertIn('content_types', facets)
        self.assertIn('date_ranges', facets)
        
        # Should have our test category
        category_names = [cat['name'] for cat in facets['categories']]
        self.assertIn("أخبار البرلمان", category_names)


class TestSEOOptimizationEngine(ContentServiceTestCase):
    """Test SEO optimization engine"""
    
    def setUp(self):
        super().setUp()
        self.seo_engine = SEOOptimizationEngine()
    
    def test_generate_seo_metadata(self):
        """Test generating SEO metadata"""
        metadata = self.seo_engine.generate_seo_metadata(self.test_content)
        
        self.assertIsNotNone(metadata.title)
        self.assertIsNotNone(metadata.description)
        self.assertIsInstance(metadata.keywords, list)
        self.assertIn("منصة نائبك", metadata.title)
        self.assertTrue(metadata.canonical_url.startswith("https://"))
    
    def test_seo_score_analysis(self):
        """Test SEO score analysis"""
        analysis = self.seo_engine.analyze_seo_score(self.test_content)
        
        self.assertIn('score', analysis)
        self.assertIn('grade', analysis)
        self.assertIn('recommendations', analysis)
        self.assertIn('breakdown', analysis)
        
        self.assertGreaterEqual(analysis['score'], 0)
        self.assertLessEqual(analysis['score'], 100)
        self.assertIn(analysis['grade'], ['A', 'B', 'C', 'D', 'F'])
    
    def test_schema_markup_generation(self):
        """Test Schema.org markup generation"""
        metadata = self.seo_engine.generate_seo_metadata(self.test_content)
        schema = metadata.schema_markup
        
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['headline'], self.test_content.title)
        self.assertIn('author', schema)
        self.assertIn('publisher', schema)
        self.assertEqual(schema['publisher']['name'], "منصة نائبك")
    
    def test_sitemap_entry_generation(self):
        """Test sitemap entry generation"""
        entry = self.seo_engine.generate_sitemap_entry(self.test_content)
        
        self.assertIn('url', entry)
        self.assertIn('lastmod', entry)
        self.assertIn('changefreq', entry)
        self.assertIn('priority', entry)
        
        self.assertTrue(entry['url'].startswith("https://"))
        self.assertGreaterEqual(entry['priority'], 0.0)
        self.assertLessEqual(entry['priority'], 1.0)


class TestContentServiceIntegration(ContentServiceTestCase):
    """Integration tests for content service"""
    
    def test_content_lifecycle(self):
        """Test complete content lifecycle"""
        # 1. Create content
        new_content_data = {
            "title": "اختبار دورة حياة المحتوى",
            "body": "هذا اختبار لدورة حياة المحتوى الكاملة",
            "content_type": "article",
            "category_id": self.test_category.id,
            "author_id": 1,
            "author_name": "كاتب الاختبار"
        }
        
        response = self.client.post(
            '/api/content',
            data=json.dumps(new_content_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        content_data = json.loads(response.data)
        content_id = content_data['id']
        
        # 2. Create version
        versioning_system = ContentVersioningSystem()
        version_result = versioning_system.create_version(
            content_id=content_id,
            user_id=1,
            version_type="manual"
        )
        self.assertIn('version_id', version_result)
        
        # 3. Moderate content
        moderation_system = ContentModerationSystem()
        moderation_result = moderation_system.moderate_content(content_id)
        self.assertIn('status', moderation_result)
        
        # 4. Publish content
        response = self.client.post(f'/api/content/{content_id}/publish')
        self.assertEqual(response.status_code, 200)
        
        # 5. Search for content
        search_engine = AdvancedSearchEngine()
        search_result = search_engine.search("دورة حياة")
        self.assertGreater(len(search_result['results']), 0)
        
        # 6. Generate SEO metadata
        content = Content.query.get(content_id)
        seo_engine = SEOOptimizationEngine()
        seo_metadata = seo_engine.generate_seo_metadata(content)
        self.assertIsNotNone(seo_metadata.title)
    
    def test_api_error_handling(self):
        """Test API error handling"""
        # Test getting non-existent content
        response = self.client.get('/api/content/99999')
        self.assertEqual(response.status_code, 404)
        
        # Test creating content with invalid data
        invalid_data = {
            "title": "",  # Empty title
            "body": "محتوى صحيح"
        }
        
        response = self.client.post(
            '/api/content',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset"""
        # Create multiple content items
        for i in range(50):
            content = Content(
                title=f"مقال الأداء {i+1}",
                body=f"محتوى مقال الأداء رقم {i+1} للاختبار",
                content_type="article",
                status="published",
                moderation_status="approved",
                author_id=1,
                author_name="كاتب الأداء",
                category_id=self.test_category.id
            )
            db.session.add(content)
        
        db.session.commit()
        
        # Test search performance
        import time
        start_time = time.time()
        
        search_engine = AdvancedSearchEngine()
        result = search_engine.search("مقال")
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Search should complete within reasonable time
        self.assertLess(search_time, 2.0)  # Less than 2 seconds
        self.assertGreater(len(result['results']), 20)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
