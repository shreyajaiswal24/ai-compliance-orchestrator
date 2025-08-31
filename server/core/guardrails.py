from pydantic import ValidationError
from typing import Dict, Any, List
import re
import json
from models.schemas import ComplianceResult

class GuardrailsManager:
    """Enforces safety policies and validates outputs"""
    
    def __init__(self):
        self.unsafe_patterns = [
            r'\b(hack|exploit|vulnerability|attack|malware|virus)\b',
            r'\b(bypass|circumvent|disable|override)\b.*\b(security|authentication|authorization)\b',
            r'\bsql\s+injection\b',
            r'\bxss\b|\bcross.site.scripting\b',
            r'\bddos\b|\bdenial.of.service\b'
        ]
        
        self.compliance_related_keywords = [
            'policy', 'compliance', 'regulation', 'audit', 'security',
            'privacy', 'gdpr', 'hipaa', 'sox', 'pci', 'iso27001',
            'authentication', 'authorization', 'access control',
            'data protection', 'encryption'
        ]
    
    def validate_query_safety(self, query: str) -> Dict[str, Any]:
        """Validate that query is compliance-related and safe"""
        
        # Check for unsafe patterns
        unsafe_matches = []
        for pattern in self.unsafe_patterns:
            matches = re.findall(pattern, query.lower())
            if matches:
                unsafe_matches.extend(matches)
        
        # Check if query is compliance-related
        compliance_score = 0
        for keyword in self.compliance_related_keywords:
            if keyword.lower() in query.lower():
                compliance_score += 1
        
        is_safe = len(unsafe_matches) == 0
        is_compliance_related = compliance_score >= 1 or len(query.split()) < 5  # Allow short queries
        
        return {
            "is_safe": is_safe,
            "is_compliance_related": is_compliance_related,
            "unsafe_matches": unsafe_matches,
            "compliance_score": compliance_score,
            "reason": self._get_validation_reason(is_safe, is_compliance_related, unsafe_matches)
        }
    
    def _get_validation_reason(self, is_safe: bool, is_compliance: bool, unsafe_matches: List[str]) -> str:
        """Generate reason for validation result"""
        if not is_safe:
            return f"Query contains potentially unsafe content: {', '.join(unsafe_matches)}"
        elif not is_compliance:
            return "Query does not appear to be compliance or risk-related"
        else:
            return "Query is acceptable for compliance analysis"
    
    def validate_result_schema(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate final result conforms to required schema"""
        try:
            # Attempt to parse as ComplianceResult
            compliance_result = ComplianceResult(**result)
            
            # Additional business logic validation
            validation_errors = []
            
            # Check decision logic consistency
            if compliance_result.decision == "compliant" and compliance_result.risk_score > 0.7:
                validation_errors.append("Inconsistent: decision is 'compliant' but risk_score is high")
            
            if compliance_result.decision == "non_compliant" and compliance_result.risk_score < 0.3:
                validation_errors.append("Inconsistent: decision is 'non_compliant' but risk_score is low")
            
            # Check confidence thresholds
            if compliance_result.confidence < 0.5 and compliance_result.decision != "insufficient_evidence":
                validation_errors.append("Low confidence should result in 'insufficient_evidence' decision")
            
            # Require citations for all decisions except insufficient_evidence
            if compliance_result.decision != "insufficient_evidence" and not compliance_result.citations:
                validation_errors.append("Compliant/non-compliant decisions must include citations")
            
            # Validate rationale quality
            if len(compliance_result.rationale) < 50:
                validation_errors.append("Rationale is too brief (minimum 50 characters)")
            
            return {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "validated_result": compliance_result.dict()
            }
            
        except ValidationError as e:
            return {
                "is_valid": False,
                "errors": [f"Schema validation error: {str(e)}"],
                "validated_result": None
            }
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Unexpected validation error: {str(e)}"],
                "validated_result": None
            }
    
    def create_safe_refusal(self, reason: str) -> ComplianceResult:
        """Create a compliant refusal response"""
        return ComplianceResult(
            decision="insufficient_evidence",
            confidence=0.0,
            risk_score=0.0,
            rationale=f"Request cannot be processed: {reason}. This system is designed for defensive compliance and risk assessment only.",
            citations=[],
            open_questions=[],
            human_interactions=[]
        )
    
    def sanitize_output(self, text: str) -> str:
        """Sanitize output text to remove potentially sensitive information"""
        
        # Remove potential API keys, tokens, passwords
        patterns_to_redact = [
            (r'\b[A-Za-z0-9]{32,}\b', '[REDACTED_TOKEN]'),  # Long alphanumeric strings
            (r'\bpassword\s*[=:]\s*\S+', 'password=[REDACTED]'),
            (r'\bapi[_-]?key\s*[=:]\s*\S+', 'api_key=[REDACTED]'),
            (r'\bsecret\s*[=:]\s*\S+', 'secret=[REDACTED]'),
            (r'\btoken\s*[=:]\s*\S+', 'token=[REDACTED]')
        ]
        
        sanitized = text
        for pattern, replacement in patterns_to_redact:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def check_rate_limit(self, session_id: str, max_requests: int = 10) -> bool:
        """Check if session has exceeded rate limits (mock implementation)"""
        # In real implementation, would check Redis/database
        # For now, always allow
        return True
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events for monitoring"""
        log_entry = {
            "timestamp": str(dict()),
            "event_type": event_type,
            "details": details
        }
        
        # In real implementation, would send to logging system
        print(f"SECURITY_EVENT: {json.dumps(log_entry)}")

# Global instance
guardrails = GuardrailsManager()