import os
import pytest
from core_logic import SecurityValidator, DBManager

def test_security_xss_sanitization():
    """Testing Coverage: Verifies that malicious scripts are neutralized."""
    unsafe_input = "<script>alert('hack')</script>"
    safe_output = SecurityValidator.sanitize(unsafe_input)
    assert "<script>" not in safe_output
    assert "&lt;script&gt;" in safe_output

def test_task_validation_edge_cases():
    """Testing Coverage: Checks edge cases in input validation."""
    # Too short
    is_valid, msg = SecurityValidator.validate_task("ab")
    assert not is_valid
    
    # Invalid characters
    is_valid, msg = SecurityValidator.validate_task("Task @#$")
    assert not is_valid
    
    # Valid
    is_valid, msg = SecurityValidator.validate_task("Valid Task Title!")
    assert is_valid

def test_rbac_access_control():
    """Testing Coverage: Ensures Role-Based Access Control functions correctly."""
    assert SecurityValidator.check_permission('Admin', 'delete_task') is True
    assert SecurityValidator.check_permission('Member', 'delete_task') is False
    assert SecurityValidator.check_permission('Viewer', 'create_task') is True

def test_database_initialization():
    """Testing Coverage: Checks database consistency."""
    DBManager.init_db()
    assert os.path.exists("data/collab_pro.db")
