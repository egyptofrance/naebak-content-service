> **Note:** This document is a work-in-progress and will be updated as the project evolves.

# Naebak Content Service: Developer Guide

**Version:** 1.0.0  
**Last Updated:** September 26, 2025  
**Author:** Manus AI

---

## 1. Service Overview

The **Naebak Content Service** is responsible for managing and delivering various types of content on the Naebak platform. It provides a flexible system for creating, storing, and retrieving articles, pages, and other content.

### **Key Features:**

-   **Content Management:** Create, update, and delete content.
-   **Content Moderation:** Review and approve user-generated content.
-   **Media Handling:** Upload and manage images, videos, and other media.
-   **Content API:** Provides an API for other services to retrieve content.

### **Technology Stack:**

-   **Framework:** Flask
-   **Database:** PostgreSQL
-   **API Documentation:** Flask-RESTX (Swagger/OpenAPI)

---

## 2. Local Development Setup

### **Prerequisites:**

-   Python 3.11+
-   Pip
-   PostgreSQL
-   Redis

### **Installation:**

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/egyptofrance/naebak-content-service.git
    cd naebak-content-service
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**

    Create a `.env` file in the root directory and add the following:

    ```env
    SECRET_KEY=your-secret-key
    DEBUG=True
    DATABASE_URL=postgres://user:password@localhost:5432/naebak_content
    REDIS_URL=redis://localhost:6379/0
    ```

4.  **Start the development server:**

    ```bash
    python app.py
    ```

    The service will be available at `http://127.0.0.1:5000`.

---

## 3. Running Tests

To run the test suite, use the following command:

```bash
python -m pytest
```

---

## 4. API Documentation

The API documentation is available at the `/` endpoint, powered by Flask-RESTX.

---

## 5. Deployment

The service is designed to be deployed as a containerized application using Docker and Google Cloud Run. A `Dockerfile` is provided for building the container image.

---

## 6. Dependencies

Key dependencies are listed in the `requirements.txt` file.

---

## 7. Contribution Guidelines

Please follow the coding standards and pull request templates defined in the central documentation hub. All contributions must pass the test suite and include relevant documentation updates.
