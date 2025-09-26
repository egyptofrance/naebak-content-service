# Naebak Content Service API Documentation

## Overview

The Naebak Content Service provides comprehensive content management capabilities for the Naebak platform, including content creation, moderation, versioning, search, and SEO optimization.

## Base URL

```
https://api.naebak.gov.eg/content
```

## Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

## Content Management APIs

### Get All Content

Retrieve a paginated list of content items.

**Endpoint:** `GET /api/content`

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)
- `status` (string, optional): Filter by status (`draft`, `published`, `archived`)
- `content_type` (string, optional): Filter by type (`news`, `article`, `announcement`)
- `category_id` (integer, optional): Filter by category ID
- `author_id` (integer, optional): Filter by author ID

**Response:**
```json
{
  "content": [
    {
      "id": 1,
      "title": "مشروع قانون جديد في البرلمان",
      "excerpt": "ملخص المحتوى...",
      "content_type": "news",
      "status": "published",
      "moderation_status": "approved",
      "author_name": "محرر الأخبار",
      "category": {
        "id": 1,
        "name": "أخبار البرلمان"
      },
      "tags": [
        {"id": 1, "name": "برلمان"},
        {"id": 2, "name": "قوانين"}
      ],
      "published_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "view_count": 150,
      "featured_image": "https://example.com/image.jpg"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

### Get Content by ID

Retrieve a specific content item by its ID.

**Endpoint:** `GET /api/content/{id}`

**Response:**
```json
{
  "id": 1,
  "title": "مشروع قانون جديد في البرلمان",
  "body": "المحتوى الكامل للمقال...",
  "excerpt": "ملخص المحتوى...",
  "content_type": "news",
  "status": "published",
  "moderation_status": "approved",
  "author_id": 1,
  "author_name": "محرر الأخبار",
  "category": {
    "id": 1,
    "name": "أخبار البرلمان",
    "slug": "parliament-news"
  },
  "tags": [
    {"id": 1, "name": "برلمان", "slug": "parliament"},
    {"id": 2, "name": "قوانين", "slug": "laws"}
  ],
  "metadata": {
    "reading_time": 5,
    "word_count": 500
  },
  "seo": {
    "title": "مشروع قانون جديد في البرلمان | منصة نائبك",
    "description": "تفاصيل مشروع القانون الجديد...",
    "keywords": ["برلمان", "قوانين", "مشروع"]
  },
  "created_at": "2024-01-15T09:00:00Z",
  "published_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "view_count": 150,
  "featured_image": "https://example.com/image.jpg"
}
```

### Create Content

Create a new content item.

**Endpoint:** `POST /api/content`

**Request Body:**
```json
{
  "title": "عنوان المحتوى",
  "body": "نص المحتوى الكامل",
  "excerpt": "ملخص المحتوى (اختياري)",
  "content_type": "news",
  "category_id": 1,
  "tags": [1, 2, 3],
  "featured_image": "https://example.com/image.jpg",
  "metadata": {
    "source": "البرلمان المصري",
    "priority": "high"
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 123,
  "title": "عنوان المحتوى",
  "status": "draft",
  "created_at": "2024-01-15T11:00:00Z",
  "message": "تم إنشاء المحتوى بنجاح"
}
```

### Update Content

Update an existing content item.

**Endpoint:** `PUT /api/content/{id}`

**Request Body:** (Same as create, all fields optional)
```json
{
  "title": "عنوان محدث",
  "body": "محتوى محدث"
}
```

**Response:** `200 OK`
```json
{
  "id": 123,
  "title": "عنوان محدث",
  "updated_at": "2024-01-15T12:00:00Z",
  "message": "تم تحديث المحتوى بنجاح"
}
```

### Delete Content

Delete a content item.

**Endpoint:** `DELETE /api/content/{id}`

**Response:** `200 OK`
```json
{
  "message": "تم حذف المحتوى بنجاح"
}
```

### Publish Content

Publish a draft content item.

**Endpoint:** `POST /api/content/{id}/publish`

**Response:** `200 OK`
```json
{
  "id": 123,
  "status": "published",
  "published_at": "2024-01-15T13:00:00Z",
  "message": "تم نشر المحتوى بنجاح"
}
```

### Archive Content

Archive a published content item.

**Endpoint:** `POST /api/content/{id}/archive`

**Response:** `200 OK`
```json
{
  "id": 123,
  "status": "archived",
  "archived_at": "2024-01-15T14:00:00Z",
  "message": "تم أرشفة المحتوى بنجاح"
}
```

## Content Moderation APIs

### Moderate Content

Submit content for moderation.

**Endpoint:** `POST /api/content/{id}/moderate`

**Request Body:**
```json
{
  "moderator_id": 1,
  "action": "approve",
  "notes": "ملاحظات المراجع"
}
```

**Response:** `200 OK`
```json
{
  "status": "approved",
  "confidence": 0.95,
  "triggered_rules": [],
  "recommendations": [],
  "moderated_at": "2024-01-15T15:00:00Z",
  "message": "تم اعتماد المحتوى"
}
```

### Get Moderation Queue

Get content items pending moderation.

**Endpoint:** `GET /api/moderation/queue`

**Query Parameters:**
- `priority` (string, optional): Filter by priority (`high`, `medium`, `low`)
- `limit` (integer, optional): Number of items to return (default: 20)

**Response:**
```json
{
  "queue": [
    {
      "id": 124,
      "title": "محتوى للمراجعة",
      "author": "كاتب المحتوى",
      "created_at": "2024-01-15T16:00:00Z",
      "priority": 3,
      "type": "article"
    }
  ],
  "total_pending": 5
}
```

### Get Moderation Statistics

Get moderation statistics for a specified period.

**Endpoint:** `GET /api/moderation/stats`

**Query Parameters:**
- `days` (integer, optional): Number of days to include (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "status_distribution": {
    "approved": 150,
    "rejected": 10,
    "flagged": 5
  },
  "automated_decisions": 120,
  "manual_decisions": 45,
  "total_moderated": 165,
  "automation_rate": 0.73
}
```

## Content Versioning APIs

### Create Version

Create a new version of content.

**Endpoint:** `POST /api/content/{id}/versions`

**Request Body:**
```json
{
  "version_type": "manual",
  "notes": "نسخة محدثة بعد المراجعة"
}
```

**Response:** `201 Created`
```json
{
  "version_id": 456,
  "version_number": 2,
  "created_at": "2024-01-15T17:00:00Z",
  "message": "تم إنشاء النسخة بنجاح"
}
```

### Get Version History

Get version history for content.

**Endpoint:** `GET /api/content/{id}/versions`

**Response:**
```json
{
  "versions": [
    {
      "id": 456,
      "version_number": 2,
      "created_at": "2024-01-15T17:00:00Z",
      "created_by": 1,
      "version_type": "manual",
      "notes": "نسخة محدثة بعد المراجعة",
      "has_changes": true
    },
    {
      "id": 455,
      "version_number": 1,
      "created_at": "2024-01-15T16:00:00Z",
      "created_by": 1,
      "version_type": "auto",
      "notes": "",
      "has_changes": true
    }
  ]
}
```

### Compare Versions

Compare two versions of content.

**Endpoint:** `GET /api/versions/{version1_id}/compare/{version2_id}`

**Response:**
```json
{
  "title_changed": true,
  "body_changed": true,
  "metadata_changed": false,
  "changes": [
    {
      "field": "title",
      "old_value": "العنوان القديم",
      "new_value": "العنوان الجديد"
    },
    {
      "field": "body",
      "change_type": "content_modified",
      "old_length": 500,
      "new_length": 750
    }
  ]
}
```

### Rollback to Version

Rollback content to a specific version.

**Endpoint:** `POST /api/content/{id}/rollback/{version_id}`

**Response:** `200 OK`
```json
{
  "success": true,
  "rolled_back_to": 1,
  "new_version": 3,
  "message": "تم التراجع إلى النسخة السابقة بنجاح"
}
```

## Search APIs

### Search Content

Search for content with advanced filtering.

**Endpoint:** `GET /api/search`

**Query Parameters:**
- `q` (string, required): Search query
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Results per page (default: 20)
- `category` (integer, optional): Category ID filter
- `tags` (array, optional): Tag IDs filter
- `content_type` (string, optional): Content type filter
- `date_from` (string, optional): Start date filter (ISO format)
- `date_to` (string, optional): End date filter (ISO format)
- `author` (integer, optional): Author ID filter

**Response:**
```json
{
  "query": "قانون البرلمان",
  "results": [
    {
      "id": 1,
      "title": "مشروع قانون جديد في البرلمان",
      "excerpt": "تم مناقشة مشروع قانون جديد...",
      "highlighted_excerpt": "تم مناقشة مشروع <mark>قانون</mark> جديد في <mark>البرلمان</mark>...",
      "content_type": "news",
      "author_name": "محرر الأخبار",
      "published_at": "2024-01-15T10:30:00Z",
      "relevance_score": 8.5,
      "url": "/content/1",
      "tags": ["برلمان", "قوانين"],
      "category": "أخبار البرلمان"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 25,
    "pages": 2
  },
  "suggestions": [
    "قوانين البرلمان",
    "جلسات البرلمان"
  ],
  "filters_applied": {
    "content_type": "news"
  }
}
```

### Search Autocomplete

Get autocomplete suggestions for search queries.

**Endpoint:** `GET /api/search/autocomplete`

**Query Parameters:**
- `q` (string, required): Partial search query
- `limit` (integer, optional): Number of suggestions (default: 10)

**Response:**
```json
{
  "suggestions": [
    "قانون البرلمان",
    "قوانين جديدة",
    "قانون الانتخابات"
  ]
}
```

### Search Facets

Get search facets for filtering.

**Endpoint:** `GET /api/search/facets`

**Query Parameters:**
- `q` (string, optional): Search query to filter facets

**Response:**
```json
{
  "categories": [
    {"id": 1, "name": "أخبار البرلمان", "count": 45},
    {"id": 2, "name": "القوانين", "count": 32}
  ],
  "content_types": [
    {"type": "news", "count": 67},
    {"type": "article", "count": 23}
  ],
  "date_ranges": [
    {"range": "last_week", "count": 15},
    {"range": "last_month", "count": 45}
  ]
}
```

## SEO APIs

### Get SEO Metadata

Get SEO metadata for content.

**Endpoint:** `GET /api/content/{id}/seo`

**Response:**
```json
{
  "title": "مشروع قانون جديد في البرلمان | منصة نائبك",
  "description": "تفاصيل مشروع القانون الجديد الذي تم مناقشته في البرلمان...",
  "keywords": ["برلمان", "قوانين", "مشروع", "نواب"],
  "canonical_url": "https://naebak.gov.eg/content/1",
  "og_title": "مشروع قانون جديد في البرلمان",
  "og_description": "تفاصيل مشروع القانون الجديد...",
  "og_image": "https://example.com/image.jpg",
  "twitter_title": "مشروع قانون جديد في البرلمان",
  "twitter_description": "تفاصيل مشروع القانون الجديد...",
  "schema_markup": {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "مشروع قانون جديد في البرلمان",
    "author": {
      "@type": "Person",
      "name": "محرر الأخبار"
    }
  }
}
```

### Analyze SEO Score

Get SEO analysis and recommendations for content.

**Endpoint:** `GET /api/content/{id}/seo/analyze`

**Response:**
```json
{
  "score": 85,
  "max_score": 100,
  "grade": "B",
  "recommendations": [
    "إضافة وصف مختصر للمحتوى",
    "تحسين استخدام الكلمات المفتاحية"
  ],
  "breakdown": {
    "title": 18,
    "content_length": 15,
    "meta_description": 10,
    "keywords": 16,
    "images": 10,
    "internal_links": 8,
    "readability": 8
  }
}
```

## Categories and Tags APIs

### Get Categories

Get all content categories.

**Endpoint:** `GET /api/categories`

**Response:**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "أخبار البرلمان",
      "description": "أخبار وتطورات البرلمان",
      "slug": "parliament-news",
      "content_count": 45
    }
  ]
}
```

### Get Tags

Get all content tags.

**Endpoint:** `GET /api/tags`

**Query Parameters:**
- `popular` (boolean, optional): Get only popular tags
- `limit` (integer, optional): Number of tags to return

**Response:**
```json
{
  "tags": [
    {
      "id": 1,
      "name": "برلمان",
      "slug": "parliament",
      "usage_count": 67
    }
  ]
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Invalid request data",
  "details": {
    "title": ["العنوان مطلوب"],
    "content_type": ["نوع المحتوى غير صحيح"]
  }
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "message": "يجب تسجيل الدخول للوصول لهذا المورد"
}
```

### 403 Forbidden
```json
{
  "error": "Access denied",
  "message": "ليس لديك صلاحية للوصول لهذا المورد"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found",
  "message": "المحتوى المطلوب غير موجود"
}
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "message": "تم تجاوز الحد المسموح من الطلبات",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "حدث خطأ في الخادم، يرجى المحاولة لاحقاً"
}
```

## Rate Limiting

API requests are rate limited to prevent abuse:

- **Authenticated users:** 1000 requests per hour
- **Search endpoints:** 100 requests per minute
- **Content creation:** 50 requests per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

## Webhooks

The Content Service supports webhooks for real-time notifications:

### Available Events

- `content.created` - New content created
- `content.published` - Content published
- `content.updated` - Content updated
- `content.moderated` - Content moderation completed
- `content.deleted` - Content deleted

### Webhook Payload Example

```json
{
  "event": "content.published",
  "timestamp": "2024-01-15T18:00:00Z",
  "data": {
    "content_id": 123,
    "title": "مشروع قانون جديد",
    "author_id": 1,
    "published_at": "2024-01-15T18:00:00Z"
  }
}
```

## SDK and Libraries

Official SDKs are available for:

- **JavaScript/Node.js:** `npm install naebak-content-sdk`
- **Python:** `pip install naebak-content-sdk`
- **PHP:** `composer require naebak/content-sdk`

## Support

For API support and questions:

- **Documentation:** https://docs.naebak.gov.eg/content-api
- **Support Email:** api-support@naebak.gov.eg
- **GitHub Issues:** https://github.com/egyptofrance/naebak-content-service/issues
