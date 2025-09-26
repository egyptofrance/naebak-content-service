# ADR-001: Content Management Architecture

**Status:** Accepted

**Context:**

The Naebak platform requires a flexible content management system to handle both static informational pages and dynamic content such as articles and announcements. We needed to design an architecture that could efficiently serve different types of content while maintaining simplicity and performance. Several approaches were considered, including a single unified content model, separate specialized models, and a hybrid approach with content versioning.

**Decision:**

We have decided to implement a dual-model content architecture that separates static pages from dynamic articles, each optimized for their specific use cases.

## **Content Model Design:**

**ContentPage Model** is designed for static, long-lived content that changes infrequently. These pages are identified by URL-friendly slugs and include content such as "About Us", "Terms of Service", "Privacy Policy", and other informational pages. The model emphasizes simplicity and direct access through memorable URLs.

**Article Model** is designed for dynamic, time-sensitive content that is published regularly. Articles support authorship attribution and are automatically ordered by publication date. This model is optimized for chronological browsing and content discovery.

## **Key Architectural Decisions:**

**Slug-Based Routing** for ContentPage enables SEO-friendly URLs and direct page access. Slugs must be unique and URL-safe, providing a natural way to organize and access static content without requiring database IDs in URLs.

**Timestamp-Driven Organization** for Articles ensures that content is naturally ordered by relevance and recency. The publish_date field serves as both a sorting mechanism and a way to track content freshness.

**Optional Author Attribution** allows the system to handle both authored content (blog posts, opinion pieces) and system-generated content (announcements, automated updates) within the same model.

**Separation of Concerns** between static and dynamic content allows for different optimization strategies, caching policies, and access patterns for each content type.

## **API Design Philosophy:**

The RESTful API follows standard HTTP conventions with clear resource separation. ContentPage endpoints use slug-based routing for natural URL patterns, while Article endpoints use ID-based routing for programmatic access. Both models support full CRUD operations with appropriate validation and error handling.

**Consequences:**

**Positive:**

*   **Performance Optimization**: Static pages can be heavily cached since they change infrequently, while dynamic articles can use different caching strategies.
*   **SEO Benefits**: Slug-based URLs for static pages provide better search engine optimization and user-friendly navigation.
*   **Content Organization**: Clear separation between static and dynamic content makes content management more intuitive for administrators.
*   **Scalability**: Different content types can be optimized independently as the platform grows.
*   **Flexibility**: The architecture can accommodate future content types without major restructuring.

**Negative:**

*   **Model Complexity**: Managing two separate models requires more code and potentially more complex queries for mixed content scenarios.
*   **Data Duplication**: Some common fields (title, content) are duplicated across models, though this is minimal.
*   **API Complexity**: Clients need to understand and interact with two different endpoint patterns for different content types.

**Implementation Notes:**

The current implementation uses SQLAlchemy ORM for database operations, which provides good abstraction and query optimization. The models include helper methods for common operations like retrieving recent articles and updating content with automatic timestamp management. Future enhancements could include content versioning, rich media support, and advanced search capabilities.
