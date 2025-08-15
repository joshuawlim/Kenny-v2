import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ResultReviewer:
    """Review and validate execution results with policy enforcement"""
    
    def __init__(self, policy_engine=None):
        self.policy_engine = policy_engine
        self.validation_rules = {
            "mail_operation": self._validate_mail_results,
            "contacts_operation": self._validate_contacts_results, 
            "memory_operation": self._validate_memory_results,
            "calendar_operation": self._validate_calendar_results
        }
    
    def review_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Review execution results and apply policy checks"""
        logger.info("Reviewing execution results")
        
        results = state.get('results', {})
        execution_results = results.get('execution_results', [])
        intent = state['context'].get('intent')
        
        review_summary = {
            "status": "success",
            "reviewed_steps": len(execution_results),
            "successful_steps": 0,
            "failed_steps": 0,
            "policy_violations": [],
            "validation_issues": [],
            "recommendations": []
        }
        
        # Review each execution step
        for result in execution_results:
            step_id = result.get('step_id')
            status = result.get('status')
            agent_id = result.get('agent_id')
            capability = result.get('capability')
            
            if status == "success":
                review_summary["successful_steps"] += 1
                
                # Apply policy checks
                policy_check = self._check_policy_compliance(result, state)
                if not policy_check["compliant"]:
                    review_summary["policy_violations"].append({
                        "step_id": step_id,
                        "violation": policy_check["violation"],
                        "action_required": policy_check["action_required"]
                    })
                
                # Apply validation rules
                validation_result = self._validate_result(result, intent)
                if not validation_result["valid"]:
                    review_summary["validation_issues"].append({
                        "step_id": step_id,
                        "issue": validation_result["issue"],
                        "severity": validation_result["severity"]
                    })
                    
            else:
                review_summary["failed_steps"] += 1
                logger.warning(f"Step {step_id} failed: {result.get('error')}")
        
        # Generate recommendations
        review_summary["recommendations"] = self._generate_recommendations(
            execution_results, review_summary, state
        )
        
        # Determine overall status
        if review_summary["policy_violations"]:
            review_summary["status"] = "policy_violation"
        elif review_summary["failed_steps"] > 0:
            review_summary["status"] = "partial_failure"
        elif review_summary["validation_issues"]:
            review_summary["status"] = "validation_warning"
        
        return review_summary
    
    def _check_policy_compliance(self, result: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if execution result complies with policies"""
        if not self.policy_engine:
            return {"compliant": True}
        
        # Create policy context for evaluation
        policy_context = {
            "agent_id": result.get('agent_id'),
            "capability": result.get('capability'),
            "operation": self._map_capability_to_operation(result.get('capability')),
            "resource": self._map_capability_to_resource(result.get('capability')),
            "user_input": state.get('user_input'),
            "execution_time": "runtime"  # Could be actual timestamp
        }
        
        try:
            policy_result = self.policy_engine.evaluate_policy(policy_context)
            final_decision = policy_result.get('final_decision')
            
            if not final_decision:
                return {"compliant": True}
            
            action = final_decision.get('action')
            
            if action == "deny":
                return {
                    "compliant": False,
                    "violation": f"Policy denies {policy_context['operation']} on {policy_context['resource']}",
                    "action_required": "block_result"
                }
            elif action == "require_approval":
                return {
                    "compliant": False,
                    "violation": f"Policy requires approval for {policy_context['operation']} on {policy_context['resource']}",
                    "action_required": "request_approval"
                }
            else:
                return {"compliant": True}
                
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            return {"compliant": True}  # Fail open for now
    
    def _validate_result(self, result: Dict[str, Any], intent: str) -> Dict[str, Any]:
        """Validate execution result based on intent-specific rules"""
        validator = self.validation_rules.get(intent)
        if not validator:
            return {"valid": True}
        
        try:
            return validator(result)
        except Exception as e:
            logger.error(f"Validation failed for {intent}: {e}")
            return {
                "valid": False,
                "issue": f"Validation error: {str(e)}",
                "severity": "warning"
            }
    
    def _validate_mail_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mail operation results"""
        result_data = result.get('result', {})
        
        if not isinstance(result_data, dict):
            return {
                "valid": False,
                "issue": "Mail result is not a dictionary",
                "severity": "error"
            }
        
        # Check for expected fields based on capability
        capability = result.get('capability', '')
        
        if capability == "messages.search":
            if 'output' not in result_data:
                return {
                    "valid": False,
                    "issue": "Mail search result missing 'output' field",
                    "severity": "error"
                }
                
            output = result_data['output']
            if not isinstance(output, dict) or 'items' not in output:
                return {
                    "valid": False,
                    "issue": "Mail search output missing 'items' field",
                    "severity": "error"
                }
        
        return {"valid": True}
    
    def _validate_contacts_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contacts operation results"""
        result_data = result.get('result', {})
        
        if not isinstance(result_data, dict):
            return {
                "valid": False,
                "issue": "Contacts result is not a dictionary",
                "severity": "error"
            }
        
        # Basic validation for contacts results
        capability = result.get('capability', '')
        
        if capability.startswith('contacts.'):
            if 'output' not in result_data:
                return {
                    "valid": False,
                    "issue": "Contacts result missing 'output' field",
                    "severity": "warning"
                }
        
        return {"valid": True}
    
    def _validate_memory_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate memory operation results"""
        result_data = result.get('result', {})
        
        if not isinstance(result_data, dict):
            return {
                "valid": False,
                "issue": "Memory result is not a dictionary",
                "severity": "error"
            }
        
        return {"valid": True}
    
    def _validate_calendar_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate calendar operation results"""
        # Calendar agent not implemented yet
        return {"valid": True}
    
    def _map_capability_to_operation(self, capability: Optional[str]) -> str:
        """Map capability to operation for policy evaluation"""
        if not capability:
            return "unknown"
        
        if capability.startswith("messages."):
            if "search" in capability or "read" in capability:
                return "mail_read"
            else:
                return "mail_write"
        elif capability.startswith("contacts."):
            return "contacts_access"
        elif capability.startswith("memory."):
            if "retrieve" in capability:
                return "memory_read"
            else:
                return "memory_write"
        elif capability.startswith("calendar."):
            return "calendar_write"
        else:
            return "general"
    
    def _map_capability_to_resource(self, capability: Optional[str]) -> str:
        """Map capability to resource for policy evaluation"""
        if not capability:
            return "unknown"
        
        if capability.startswith("messages."):
            return "mail"
        elif capability.startswith("contacts."):
            return "contacts"
        elif capability.startswith("memory."):
            return "memory"
        elif capability.startswith("calendar."):
            return "calendar"
        else:
            return "general"
    
    def _generate_recommendations(self, execution_results: List[Dict], review_summary: Dict, state: Dict) -> List[str]:
        """Generate recommendations based on review results"""
        recommendations = []
        
        # Performance recommendations
        successful_count = review_summary["successful_steps"]
        total_count = review_summary["reviewed_steps"]
        
        if total_count > 0:
            success_rate = successful_count / total_count
            if success_rate < 0.8:
                recommendations.append("Consider simplifying the request or checking agent availability")
        
        # Policy recommendations
        if review_summary["policy_violations"]:
            recommendations.append("Some operations require policy approval - consider requesting permissions")
        
        # Validation recommendations
        validation_issues = review_summary["validation_issues"]
        error_issues = [v for v in validation_issues if v.get("severity") == "error"]
        if error_issues:
            recommendations.append("Some results have validation errors - verify agent implementations")
        
        # Intent-specific recommendations
        intent = state['context'].get('intent')
        if intent == "mail_operation" and successful_count > 0:
            recommendations.append("Mail operation completed - consider enabling notifications for new messages")
        elif intent == "contacts_operation" and successful_count > 0:
            recommendations.append("Contact information retrieved - consider enriching with additional sources")
        
        return recommendations

class ReviewerNode:
    """Enhanced reviewer node with policy integration and result validation"""
    
    def __init__(self, policy_engine=None):
        self.reviewer = ResultReviewer(policy_engine)
    
    async def review_execution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Review and finalize execution results"""
        logger.info("Reviewing execution results")
        state['current_node'] = "reviewer"
        state['execution_path'].append("reviewer")
        
        try:
            # Perform comprehensive review
            review_summary = self.reviewer.review_results(state)
            
            # Store review results
            state['context']['review_summary'] = review_summary
            
            # Log review results
            status = review_summary['status']
            successful = review_summary['successful_steps']
            total = review_summary['reviewed_steps']
            
            if status == "success":
                logger.info(f"Review completed successfully: {successful}/{total} steps succeeded")
            elif status == "policy_violation":
                logger.warning(f"Review found policy violations: {successful}/{total} steps succeeded")
            elif status == "partial_failure":
                logger.warning(f"Review found failures: {successful}/{total} steps succeeded")
            else:
                logger.info(f"Review completed with warnings: {successful}/{total} steps succeeded")
            
            # Add review errors to state if needed
            if review_summary['policy_violations']:
                for violation in review_summary['policy_violations']:
                    state['errors'].append(f"Policy violation in {violation['step_id']}: {violation['violation']}")
            
        except Exception as e:
            logger.error(f"Error in review: {e}")
            state['errors'].append(f"Review error: {str(e)}")
            # Add minimal review summary
            state['context']['review_summary'] = {
                "status": "review_error",
                "reviewed_steps": 0,
                "successful_steps": 0,
                "failed_steps": 0,
                "error": str(e)
            }
        
        return state