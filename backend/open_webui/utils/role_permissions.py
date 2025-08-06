from open_webui.roles import ROLES
from typing import Optional

def has_role_permission(user_role: str, permission: str) -> bool:
    """
    Check if a user role has a specific permission.
    
    Args:
        user_role: The user's role (admin, teacher, student, user)
        permission: The permission to check
        
    Returns:
        bool: True if the role has the permission, False otherwise
    """
    if user_role not in ROLES:
        return False
    
    return ROLES[user_role].get(permission, False)

def get_role_permissions(user_role: str) -> dict:
    """
    Get all permissions for a user role.
    
    Args:
        user_role: The user's role
        
    Returns:
        dict: Dictionary of permissions for the role
    """
    return ROLES.get(user_role, {})

def can_upload_documents(user_role: str) -> bool:
    """Check if user can upload documents (only teachers and admins)"""
    return has_role_permission(user_role, "can_upload_documents")

def can_edit_documents(user_role: str) -> bool:
    """Check if user can edit documents (only teachers and admins)"""
    return has_role_permission(user_role, "can_edit_documents")

def can_delete_documents(user_role: str) -> bool:
    """Check if user can delete documents (only teachers and admins)"""
    return has_role_permission(user_role, "can_delete_documents")

def can_submit_code(user_role: str) -> bool:
    """Check if user can submit code/text for review (students, teachers, admins)"""
    return has_role_permission(user_role, "can_submit_code")

def can_access_workspace(user_role: str) -> bool:
    """Check if user can access workspace (all except basic user)"""
    return has_role_permission(user_role, "can_access_workspace")

def get_allowed_roles() -> list:
    """Get list of all allowed roles"""
    return list(ROLES.keys())

def validate_role(role: str) -> bool:
    """Validate if role exists"""
    return role in ROLES
