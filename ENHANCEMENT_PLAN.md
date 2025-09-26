# Naebak Content Service - Enhancement Plan

## 1. Current State Analysis

The content service currently provides basic CRUD functionality for two content types: `ContentPage` (for static pages) and `Article` (for dynamic content). While functional, it lacks several advanced features required for a robust content management system.

### Key Deficiencies:

1.  **Limited Content Organization:** No support for categories, tags, or other taxonomies.
2.  **No Content Moderation:** Content is published immediately without any review or approval workflow.
3.  **No Version History:** Changes to content are destructive and cannot be rolled back.
4.  **No Search Functionality:** The service lacks a dedicated search endpoint.
5.  **No SEO Support:** No fields for SEO metadata (meta titles, descriptions, keywords).
6.  **Basic Media Handling:** No dedicated system for managing images, videos, or other media.

## 2. Proposed Enhancements

This plan outlines the key enhancements to transform the content service into a full-featured CMS.

### 2.1. Enhance Core Models and Database Schema

-   **Add `Category` and `Tag` models:** For content organization.
-   **Create many-to-many relationships:** Link articles to categories and tags.
-   **Add `ContentVersion` model:** To store historical versions of content.
-   **Add `Media` model:** For managing uploaded media files.
-   **Add SEO fields:** `meta_title`, `meta_description`, `meta_keywords` to `Article` and `ContentPage`.
-   **Add moderation fields:** `status` (draft, pending, published, archived), `moderator_id`, `moderation_notes`.

### 2.2. Develop Advanced Content Management APIs

-   **Taxonomy Endpoints:** CRUD endpoints for `/categories` and `/tags`.
-   **Content Status Endpoints:** Endpoints to manage content lifecycle (e.g., `POST /articles/{id}/publish`).
-   **Media Upload Endpoint:** A dedicated endpoint for uploading and managing media.

### 2.3. Implement Content Moderation and Versioning

-   **Moderation Workflow:** Implement logic to handle content status changes.
-   **Versioning System:** Automatically create new versions of content on update.
-   **Rollback Endpoint:** An endpoint to restore a previous version of content.

### 2.4. Add Search Functionality and SEO Optimization

-   **Search Endpoint:** A dedicated `/search` endpoint with support for full-text search.
-   **SEO Metadata API:** Endpoints to manage SEO metadata for content.

### 2.5. Create Comprehensive Tests and Documentation

-   **Test Suite:** Expand the test suite to cover all new functionality.
-   **API Documentation:** Update the API documentation to reflect all new endpoints and features.

## 3. Development Phases

1.  **Phase 1: Database and Model Enhancements** (1-2 days)
2.  **Phase 2: Advanced API Development** (2-3 days)
3.  **Phase 3: Moderation and Versioning** (2-3 days)
4.  **Phase 4: Search and SEO** (1-2 days)
5.  **Phase 5: Testing and Documentation** (2-3 days)

**Estimated Total Time:** 8-13 days
