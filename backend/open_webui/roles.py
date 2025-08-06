ROLES = {
    "admin": {
        "can_upload": True,
        "can_instruct": True,
        "can_view": True,
        "can_manage_users": True,
        "can_manage_permissions": True,
        "can_access_workspace": True,
        "can_upload_documents": True,
        "can_edit_documents": True,
        "can_delete_documents": True,
        "can_submit_code": True
    },
    "teacher": {
        "can_upload": True,
        "can_instruct": True,
        "can_view": True,
        "can_manage_users": False,
        "can_manage_permissions": False,
        "can_access_workspace": True,
        "can_upload_documents": True,
        "can_edit_documents": True,
        "can_delete_documents": True,
        "can_submit_code": True
    },
    "student": {
        "can_upload": False,
        "can_instruct": False,
        "can_view": True,
        "can_manage_users": False,
        "can_manage_permissions": False,
        "can_access_workspace": True,
        "can_upload_documents": False,
        "can_edit_documents": False,
        "can_delete_documents": False,
        "can_submit_code": True
    },
    "user": {
        "can_upload": False,
        "can_instruct": False,
        "can_view": False,
        "can_manage_users": False,
        "can_manage_permissions": False,
        "can_access_workspace": False,
        "can_upload_documents": False,
        "can_edit_documents": False,
        "can_delete_documents": False,
        "can_submit_code": False
    },
    "pending": {
        "can_upload": False,
        "can_instruct": False,
        "can_view": False,
        "can_manage_users": False,
        "can_manage_permissions": False,
        "can_access_workspace": False,
        "can_upload_documents": False,
        "can_edit_documents": False,
        "can_delete_documents": False,
        "can_submit_code": False
    }
}