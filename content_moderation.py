"""
Content Moderation and Versioning System for Naebak Content Service

This module provides comprehensive content moderation capabilities and version control
for all content types in the Naebak platform.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import hashlib
from dataclasses import dataclass

from flask import current_app
from sqlalchemy import and_, or_
from models import db, Content, ContentVersion, ModerationLog


class ModerationStatus(Enum):
    """Content moderation status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    UNDER_REVIEW = "under_review"


class ModerationAction(Enum):
    """Moderation action types"""
    APPROVE = "approve"
    REJECT = "reject"
    FLAG = "flag"
    UNFLAG = "unflag"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"


@dataclass
class ModerationRule:
    """Content moderation rule definition"""
    name: str
    description: str
    severity: str  # low, medium, high, critical
    auto_action: Optional[str] = None
    requires_human_review: bool = False


class ContentModerationSystem:
    """
    Advanced content moderation system with automated and manual review capabilities.
    
    Features:
    - Automated content scanning
    - Manual review workflows
    - Escalation procedures
    - Audit trails
    - Performance metrics
    """
    
    def __init__(self):
        self.moderation_rules = self._load_moderation_rules()
        self.auto_moderation_enabled = True
        self.human_review_threshold = 0.7
    
    def _load_moderation_rules(self) -> List[ModerationRule]:
        """Load content moderation rules from configuration"""
        return [
            ModerationRule(
                name="inappropriate_language",
                description="Content contains inappropriate or offensive language",
                severity="high",
                auto_action="flag",
                requires_human_review=True
            ),
            ModerationRule(
                name="political_bias",
                description="Content shows extreme political bias",
                severity="medium",
                requires_human_review=True
            ),
            ModerationRule(
                name="factual_accuracy",
                description="Content may contain factual inaccuracies",
                severity="high",
                requires_human_review=True
            ),
            ModerationRule(
                name="spam_content",
                description="Content appears to be spam or promotional",
                severity="medium",
                auto_action="reject"
            ),
            ModerationRule(
                name="duplicate_content",
                description="Content is duplicate or near-duplicate",
                severity="low",
                auto_action="flag"
            )
        ]
    
    def moderate_content(self, content_id: int, moderator_id: int = None) -> Dict[str, Any]:
        """
        Perform comprehensive content moderation
        
        Args:
            content_id: ID of content to moderate
            moderator_id: ID of human moderator (if manual review)
            
        Returns:
            Moderation result with status and recommendations
        """
        try:
            content = Content.query.get(content_id)
            if not content:
                return {"error": "Content not found"}
            
            # Run automated moderation checks
            auto_result = self._run_automated_moderation(content)
            
            # Determine if human review is needed
            needs_human_review = (
                auto_result["confidence"] < self.human_review_threshold or
                any(rule.requires_human_review for rule in auto_result["triggered_rules"])
            )
            
            if needs_human_review and not moderator_id:
                # Queue for human review
                return self._queue_for_human_review(content, auto_result)
            
            # Apply moderation decision
            final_status = self._determine_final_status(auto_result, moderator_id)
            
            # Update content status
            content.moderation_status = final_status.value
            content.moderated_at = datetime.utcnow()
            content.moderated_by = moderator_id
            
            # Log moderation action
            self._log_moderation_action(
                content_id=content_id,
                moderator_id=moderator_id,
                action=final_status.value,
                details=auto_result,
                is_automated=moderator_id is None
            )
            
            db.session.commit()
            
            return {
                "status": final_status.value,
                "confidence": auto_result["confidence"],
                "triggered_rules": [rule.name for rule in auto_result["triggered_rules"]],
                "recommendations": auto_result["recommendations"],
                "needs_human_review": needs_human_review
            }
            
        except Exception as e:
            current_app.logger.error(f"Content moderation error: {str(e)}")
            return {"error": "Moderation failed"}
    
    def _run_automated_moderation(self, content: Content) -> Dict[str, Any]:
        """Run automated content moderation checks"""
        triggered_rules = []
        confidence_scores = []
        recommendations = []
        
        # Check for inappropriate language
        if self._check_inappropriate_language(content.body):
            triggered_rules.append(self.moderation_rules[0])
            confidence_scores.append(0.9)
            recommendations.append("Review language for appropriateness")
        
        # Check for political bias
        bias_score = self._check_political_bias(content.body)
        if bias_score > 0.7:
            triggered_rules.append(self.moderation_rules[1])
            confidence_scores.append(bias_score)
            recommendations.append("Review for political neutrality")
        
        # Check for factual accuracy indicators
        if self._check_factual_concerns(content.body):
            triggered_rules.append(self.moderation_rules[2])
            confidence_scores.append(0.6)
            recommendations.append("Verify factual claims")
        
        # Check for spam indicators
        spam_score = self._check_spam_indicators(content)
        if spam_score > 0.8:
            triggered_rules.append(self.moderation_rules[3])
            confidence_scores.append(spam_score)
            recommendations.append("Content appears promotional")
        
        # Check for duplicate content
        if self._check_duplicate_content(content):
            triggered_rules.append(self.moderation_rules[4])
            confidence_scores.append(0.8)
            recommendations.append("Similar content exists")
        
        # Calculate overall confidence
        overall_confidence = max(confidence_scores) if confidence_scores else 1.0
        
        return {
            "triggered_rules": triggered_rules,
            "confidence": overall_confidence,
            "recommendations": recommendations,
            "scores": {
                "bias": bias_score if 'bias_score' in locals() else 0,
                "spam": spam_score if 'spam_score' in locals() else 0
            }
        }
    
    def _check_inappropriate_language(self, text: str) -> bool:
        """Check for inappropriate or offensive language"""
        # Simplified implementation - in production, use advanced NLP
        inappropriate_words = [
            "كلمات غير لائقة", "محتوى مسيء", "لغة عدائية"
        ]
        text_lower = text.lower()
        return any(word in text_lower for word in inappropriate_words)
    
    def _check_political_bias(self, text: str) -> float:
        """Check for extreme political bias (returns score 0-1)"""
        # Simplified implementation - in production, use ML models
        bias_indicators = [
            "متطرف", "عدو", "خائن", "فاسد", "مؤامرة"
        ]
        text_lower = text.lower()
        matches = sum(1 for indicator in bias_indicators if indicator in text_lower)
        return min(matches * 0.3, 1.0)
    
    def _check_factual_concerns(self, text: str) -> bool:
        """Check for potential factual accuracy concerns"""
        # Simplified implementation
        concern_phrases = [
            "بدون مصدر", "شائعات", "غير مؤكد", "قيل أن"
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in concern_phrases)
    
    def _check_spam_indicators(self, content: Content) -> float:
        """Check for spam indicators (returns score 0-1)"""
        spam_score = 0.0
        
        # Check for excessive links
        if content.body.count('http') > 3:
            spam_score += 0.3
        
        # Check for promotional language
        promo_words = ["اشتري", "خصم", "عرض", "مجاني", "اتصل الآن"]
        matches = sum(1 for word in promo_words if word in content.body.lower())
        spam_score += matches * 0.2
        
        # Check for repetitive content
        words = content.body.split()
        if len(set(words)) < len(words) * 0.5:  # Less than 50% unique words
            spam_score += 0.4
        
        return min(spam_score, 1.0)
    
    def _check_duplicate_content(self, content: Content) -> bool:
        """Check for duplicate or near-duplicate content"""
        # Create content hash for comparison
        content_hash = hashlib.md5(content.body.encode()).hexdigest()
        
        # Check for exact duplicates
        existing = Content.query.filter(
            and_(
                Content.content_hash == content_hash,
                Content.id != content.id
            )
        ).first()
        
        return existing is not None
    
    def _queue_for_human_review(self, content: Content, auto_result: Dict) -> Dict[str, Any]:
        """Queue content for human review"""
        content.moderation_status = ModerationStatus.UNDER_REVIEW.value
        content.review_priority = self._calculate_review_priority(auto_result)
        
        db.session.commit()
        
        return {
            "status": "queued_for_review",
            "priority": content.review_priority,
            "auto_analysis": auto_result
        }
    
    def _calculate_review_priority(self, auto_result: Dict) -> int:
        """Calculate review priority (1-5, 5 being highest)"""
        high_severity_rules = [
            rule for rule in auto_result["triggered_rules"]
            if rule.severity == "high"
        ]
        
        if high_severity_rules:
            return 5
        elif auto_result["confidence"] < 0.3:
            return 4
        elif len(auto_result["triggered_rules"]) > 2:
            return 3
        else:
            return 2
    
    def _determine_final_status(self, auto_result: Dict, moderator_id: int = None) -> ModerationStatus:
        """Determine final moderation status"""
        if moderator_id:
            # Human moderator decision takes precedence
            # This would be determined by the moderator's input
            return ModerationStatus.APPROVED  # Placeholder
        
        # Automated decision based on rules
        critical_rules = [
            rule for rule in auto_result["triggered_rules"]
            if rule.severity in ["high", "critical"]
        ]
        
        if critical_rules:
            auto_actions = [rule.auto_action for rule in critical_rules if rule.auto_action]
            if "reject" in auto_actions:
                return ModerationStatus.REJECTED
            elif "flag" in auto_actions:
                return ModerationStatus.FLAGGED
        
        return ModerationStatus.APPROVED
    
    def _log_moderation_action(self, content_id: int, moderator_id: int, 
                             action: str, details: Dict, is_automated: bool = False):
        """Log moderation action for audit trail"""
        log_entry = ModerationLog(
            content_id=content_id,
            moderator_id=moderator_id,
            action=action,
            details=json.dumps(details),
            is_automated=is_automated,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(log_entry)
    
    def get_moderation_queue(self, moderator_id: int, limit: int = 20) -> List[Dict]:
        """Get content items pending human review"""
        pending_content = Content.query.filter(
            Content.moderation_status == ModerationStatus.UNDER_REVIEW.value
        ).order_by(Content.review_priority.desc(), Content.created_at.asc()).limit(limit).all()
        
        return [
            {
                "id": content.id,
                "title": content.title,
                "author": content.author_name,
                "created_at": content.created_at.isoformat(),
                "priority": content.review_priority,
                "type": content.content_type
            }
            for content in pending_content
        ]
    
    def get_moderation_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get moderation statistics for the specified period"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get moderation counts by status
        status_counts = db.session.query(
            Content.moderation_status,
            db.func.count(Content.id)
        ).filter(
            Content.moderated_at >= start_date
        ).group_by(Content.moderation_status).all()
        
        # Get automated vs manual moderation counts
        auto_count = ModerationLog.query.filter(
            and_(
                ModerationLog.timestamp >= start_date,
                ModerationLog.is_automated == True
            )
        ).count()
        
        manual_count = ModerationLog.query.filter(
            and_(
                ModerationLog.timestamp >= start_date,
                ModerationLog.is_automated == False
            )
        ).count()
        
        return {
            "period_days": days,
            "status_distribution": dict(status_counts),
            "automated_decisions": auto_count,
            "manual_decisions": manual_count,
            "total_moderated": auto_count + manual_count,
            "automation_rate": auto_count / (auto_count + manual_count) if (auto_count + manual_count) > 0 else 0
        }


class ContentVersioningSystem:
    """
    Advanced content versioning system with change tracking and rollback capabilities.
    
    Features:
    - Automatic version creation
    - Change tracking and diff generation
    - Version comparison
    - Rollback functionality
    - Branch management
    """
    
    def __init__(self):
        self.max_versions_per_content = 50
        self.auto_version_on_publish = True
    
    def create_version(self, content_id: int, user_id: int, 
                      version_type: str = "auto", notes: str = "") -> Dict[str, Any]:
        """
        Create a new version of content
        
        Args:
            content_id: ID of the content
            user_id: ID of the user creating the version
            version_type: Type of version (auto, manual, publish, rollback)
            notes: Optional notes about the version
            
        Returns:
            Version creation result
        """
        try:
            content = Content.query.get(content_id)
            if not content:
                return {"error": "Content not found"}
            
            # Get current version number
            latest_version = ContentVersion.query.filter_by(
                content_id=content_id
            ).order_by(ContentVersion.version_number.desc()).first()
            
            next_version = (latest_version.version_number + 1) if latest_version else 1
            
            # Create version snapshot
            version = ContentVersion(
                content_id=content_id,
                version_number=next_version,
                title=content.title,
                body=content.body,
                metadata=json.dumps(content.metadata or {}),
                created_by=user_id,
                version_type=version_type,
                notes=notes,
                content_hash=self._calculate_content_hash(content),
                created_at=datetime.utcnow()
            )
            
            db.session.add(version)
            
            # Clean up old versions if needed
            self._cleanup_old_versions(content_id)
            
            db.session.commit()
            
            return {
                "version_id": version.id,
                "version_number": version.version_number,
                "created_at": version.created_at.isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"Version creation error: {str(e)}")
            return {"error": "Version creation failed"}
    
    def _calculate_content_hash(self, content: Content) -> str:
        """Calculate hash of content for change detection"""
        content_string = f"{content.title}{content.body}{json.dumps(content.metadata or {})}"
        return hashlib.sha256(content_string.encode()).hexdigest()
    
    def _cleanup_old_versions(self, content_id: int):
        """Remove old versions beyond the maximum limit"""
        version_count = ContentVersion.query.filter_by(content_id=content_id).count()
        
        if version_count >= self.max_versions_per_content:
            # Keep the most recent versions and important milestones
            versions_to_delete = ContentVersion.query.filter_by(
                content_id=content_id
            ).filter(
                ContentVersion.version_type != "publish"  # Keep published versions
            ).order_by(
                ContentVersion.version_number.asc()
            ).limit(version_count - self.max_versions_per_content + 5).all()
            
            for version in versions_to_delete:
                db.session.delete(version)
    
    def get_version_history(self, content_id: int, limit: int = 20) -> List[Dict]:
        """Get version history for content"""
        versions = ContentVersion.query.filter_by(
            content_id=content_id
        ).order_by(
            ContentVersion.version_number.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": version.id,
                "version_number": version.version_number,
                "created_at": version.created_at.isoformat(),
                "created_by": version.created_by,
                "version_type": version.version_type,
                "notes": version.notes,
                "has_changes": self._has_significant_changes(version)
            }
            for version in versions
        ]
    
    def _has_significant_changes(self, version: ContentVersion) -> bool:
        """Check if version has significant changes from previous version"""
        previous_version = ContentVersion.query.filter(
            and_(
                ContentVersion.content_id == version.content_id,
                ContentVersion.version_number < version.version_number
            )
        ).order_by(ContentVersion.version_number.desc()).first()
        
        if not previous_version:
            return True
        
        # Compare content hashes
        return version.content_hash != previous_version.content_hash
    
    def compare_versions(self, version1_id: int, version2_id: int) -> Dict[str, Any]:
        """Compare two versions and generate diff"""
        version1 = ContentVersion.query.get(version1_id)
        version2 = ContentVersion.query.get(version2_id)
        
        if not version1 or not version2:
            return {"error": "Version not found"}
        
        if version1.content_id != version2.content_id:
            return {"error": "Versions belong to different content"}
        
        # Generate diff (simplified implementation)
        diff = {
            "title_changed": version1.title != version2.title,
            "body_changed": version1.body != version2.body,
            "metadata_changed": version1.metadata != version2.metadata,
            "changes": []
        }
        
        if diff["title_changed"]:
            diff["changes"].append({
                "field": "title",
                "old_value": version1.title,
                "new_value": version2.title
            })
        
        if diff["body_changed"]:
            diff["changes"].append({
                "field": "body",
                "change_type": "content_modified",
                "old_length": len(version1.body),
                "new_length": len(version2.body)
            })
        
        return diff
    
    def rollback_to_version(self, content_id: int, version_id: int, user_id: int) -> Dict[str, Any]:
        """Rollback content to a specific version"""
        try:
            content = Content.query.get(content_id)
            version = ContentVersion.query.get(version_id)
            
            if not content or not version:
                return {"error": "Content or version not found"}
            
            if version.content_id != content_id:
                return {"error": "Version does not belong to this content"}
            
            # Create a backup of current state
            self.create_version(
                content_id=content_id,
                user_id=user_id,
                version_type="rollback_backup",
                notes=f"Backup before rollback to version {version.version_number}"
            )
            
            # Restore content from version
            content.title = version.title
            content.body = version.body
            content.metadata = json.loads(version.metadata) if version.metadata else {}
            content.updated_at = datetime.utcnow()
            content.updated_by = user_id
            
            # Create rollback version
            rollback_version = self.create_version(
                content_id=content_id,
                user_id=user_id,
                version_type="rollback",
                notes=f"Rolled back to version {version.version_number}"
            )
            
            db.session.commit()
            
            return {
                "success": True,
                "rolled_back_to": version.version_number,
                "new_version": rollback_version["version_number"]
            }
            
        except Exception as e:
            current_app.logger.error(f"Rollback error: {str(e)}")
            return {"error": "Rollback failed"}
    
    def get_version_details(self, version_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific version"""
        version = ContentVersion.query.get(version_id)
        
        if not version:
            return {"error": "Version not found"}
        
        return {
            "id": version.id,
            "content_id": version.content_id,
            "version_number": version.version_number,
            "title": version.title,
            "body": version.body,
            "metadata": json.loads(version.metadata) if version.metadata else {},
            "created_at": version.created_at.isoformat(),
            "created_by": version.created_by,
            "version_type": version.version_type,
            "notes": version.notes,
            "content_hash": version.content_hash
        }


# Initialize systems
moderation_system = ContentModerationSystem()
versioning_system = ContentVersioningSystem()
