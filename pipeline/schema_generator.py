import json

def generate_schemas(blueprint: dict, inject_bug: bool = True) -> dict:
    """
    Stage 3: Schema Generation
    Generates UI, API, DB, Auth, and Business Logic schemas from SystemBlueprint.
    If inject_bug = True, a cross-layer validation inconsistency is intentionally injected.
    """
    entities = blueprint.get("entities", ["user"])
    pages = blueprint.get("pages", ["/login", "/register", "/dashboard"])
    permissions = blueprint.get("permissions", {})
    
    app_type = "crm"
    if "task" in "".join(pages):
        app_type = "task"
    elif "product" in "".join(pages):
        app_type = "ecommerce"
    elif "item" in "".join(pages):
        app_type = "inventory"
    elif "post" in "".join(pages):
        app_type = "content"

    # 1. UI Schema
    ui_schema = {
        "pages": pages,
        "components": [
            {"name": "LoginForm", "type": "Form", "fields": ["email", "password"], "submit_target": "/api/v1/auth/login"},
            {"name": "RegisterForm", "type": "Form", "fields": ["email", "password"], "submit_target": "/api/v1/auth/register"}
        ],
        "form_fields": {
            "email": {"type": "string", "label": "Email Address", "required": True},
            "password": {"type": "string", "label": "Password", "required": True}
        },
        "navigation": [
            {"label": "Dashboard", "path": "/dashboard", "icon": "Home"}
        ]
    }
    
    # App specific UI components and navigation
    if app_type == "crm":
        ui_schema["components"].append({
            "name": "ContactForm",
            "type": "Form",
            "fields": ["name", "email", "phone"],
            "submit_target": "/api/v1/contacts"
        })
        ui_schema["form_fields"].update({
            "name": {"type": "string", "label": "Full Name", "required": True},
            "phone": {"type": "string", "label": "Phone Number", "required": False}
        })
        ui_schema["navigation"].append({"label": "Contacts", "path": "/contacts", "icon": "Users"})
        
    elif app_type == "task":
        ui_schema["components"].append({
            "name": "TaskForm",
            "type": "Form",
            "fields": ["title", "description", "status"],
            "submit_target": "/api/v1/tasks"
        })
        ui_schema["form_fields"].update({
            "title": {"type": "string", "label": "Task Title", "required": True},
            "description": {"type": "string", "label": "Description", "required": False},
            "status": {"type": "string", "label": "Status", "required": True}
        })
        ui_schema["navigation"].append({"label": "Tasks", "path": "/tasks", "icon": "CheckSquare"})
        
    elif app_type == "ecommerce":
        ui_schema["components"].append({
            "name": "CheckoutForm",
            "type": "Form",
            "fields": ["shipping_address", "card_number"],
            "submit_target": "/api/v1/orders"
        })
        ui_schema["form_fields"].update({
            "shipping_address": {"type": "string", "label": "Shipping Address", "required": True},
            "card_number": {"type": "string", "label": "Credit Card Number", "required": True}
        })
        ui_schema["navigation"].extend([
            {"label": "Products", "path": "/products", "icon": "ShoppingBag"},
            {"label": "Orders", "path": "/orders", "icon": "Receipt"}
        ])

    elif app_type == "inventory":
        ui_schema["components"].append({
            "name": "StockAdjustmentForm",
            "type": "Form",
            "fields": ["item_id", "quantity_delta"],
            "submit_target": "/api/v1/inventory/adjust"
        })
        ui_schema["form_fields"].update({
            "item_id": {"type": "integer", "label": "Item ID", "required": True},
            "quantity_delta": {"type": "integer", "label": "Adjustment Quantity", "required": True}
        })
        ui_schema["navigation"].append({"label": "Inventory", "path": "/inventory", "icon": "Archive"})

    elif app_type == "content":
        ui_schema["components"].append({
            "name": "PostForm",
            "type": "Form",
            "fields": ["title", "content", "category"],
            "submit_target": "/api/v1/posts"
        })
        ui_schema["form_fields"].update({
            "title": {"type": "string", "label": "Post Title", "required": True},
            "content": {"type": "string", "label": "Article Content", "required": True},
            "category": {"type": "string", "label": "Category", "required": False}
        })
        ui_schema["navigation"].append({"label": "Articles", "path": "/posts", "icon": "BookOpen"})

    # Admin dashboard pages
    if "/admin/analytics" in pages:
        ui_schema["navigation"].append({"label": "Analytics", "path": "/admin/analytics", "icon": "TrendingUp"})
    if "/billing" in pages:
        ui_schema["navigation"].append({"label": "Billing", "path": "/billing", "icon": "CreditCard"})

    # 2. API Schema
    routes = [
        {
            "path": "/api/v1/auth/login",
            "method": "POST",
            "request_model": {
                "properties": {
                    "email": {"type": "string"},
                    "password": {"type": "string"}
                },
                "required": ["email", "password"]
            },
            "response_model": "user",
            "auth_required": False,
            "roles": []
        },
        {
            "path": "/api/v1/auth/register",
            "method": "POST",
            "request_model": {
                "properties": {
                    "email": {"type": "string"},
                    "password": {"type": "string"}
                },
                "required": ["email", "password"]
            },
            "response_model": "user",
            "auth_required": False,
            "roles": []
        }
    ]
    
    # App specific API routes
    if app_type == "crm":
        routes.extend([
            {
                "path": "/api/v1/contacts",
                "method": "GET",
                "request_model": None,
                "response_model": "contact_list",
                "auth_required": True,
                "roles": ["User", "Admin", "PremiumUser"]
            },
            {
                "path": "/api/v1/contacts",
                "method": "POST",
                "request_model": {
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"}
                    },
                    "required": ["name"]
                },
                "response_model": "contact",
                "auth_required": True,
                "roles": ["User", "Admin", "PremiumUser"]
            },
            {
                "path": "/api/v1/contacts/{id}",
                "method": "DELETE",
                "request_model": None,
                "response_model": "delete_status",
                "auth_required": True,
                "roles": ["Admin", "Manager"]
            }
        ])
    elif app_type == "task":
        routes.extend([
            {
                "path": "/api/v1/tasks",
                "method": "GET",
                "request_model": None,
                "response_model": "task_list",
                "auth_required": True,
                "roles": ["User", "Admin"]
            },
            {
                "path": "/api/v1/tasks",
                "method": "POST",
                "request_model": {
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string"}
                    },
                    "required": ["title", "status"]
                },
                "response_model": "task",
                "auth_required": True,
                "roles": ["User", "Admin"]
            }
        ])
    elif app_type == "ecommerce":
        routes.extend([
            {
                "path": "/api/v1/products",
                "method": "GET",
                "request_model": None,
                "response_model": "product_list",
                "auth_required": False,
                "roles": []
            },
            {
                "path": "/api/v1/orders",
                "method": "POST",
                "request_model": {
                    "properties": {
                        "shipping_address": {"type": "string"},
                        "card_number": {"type": "string"}
                    },
                    "required": ["shipping_address", "card_number"]
                },
                "response_model": "order",
                "auth_required": True,
                "roles": ["User", "Admin"]
            }
        ])
    elif app_type == "inventory":
        routes.extend([
            {
                "path": "/api/v1/inventory",
                "method": "GET",
                "request_model": None,
                "response_model": "inventory_list",
                "auth_required": True,
                "roles": ["User", "Admin"]
            },
            {
                "path": "/api/v1/inventory/adjust",
                "method": "POST",
                "request_model": {
                    "properties": {
                        "item_id": {"type": "integer"},
                        "quantity_delta": {"type": "integer"}
                    },
                    "required": ["item_id", "quantity_delta"]
                },
                "response_model": "inventory_item",
                "auth_required": True,
                "roles": ["Admin", "Manager", "User"]
            }
        ])
    elif app_type == "content":
        routes.extend([
            {
                "path": "/api/v1/posts",
                "method": "GET",
                "request_model": None,
                "response_model": "post_list",
                "auth_required": False,
                "roles": []
            },
            {
                "path": "/api/v1/posts",
                "method": "POST",
                "request_model": {
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "category": {"type": "string"}
                    },
                    "required": ["title", "content"]
                },
                "response_model": "post",
                "auth_required": True,
                "roles": ["PremiumUser", "Admin"]
            }
        ])

    # Shared conditional routes
    if "/admin/analytics" in pages:
        routes.append({
            "path": "/api/v1/analytics/overview",
            "method": "GET",
            "request_model": None,
            "response_model": "analytics_summary",
            "auth_required": True,
            "roles": ["Admin"]
        })
    if "/billing" in pages:
        routes.append({
            "path": "/api/v1/billing/checkout",
            "method": "POST",
            "request_model": {
                "properties": {
                    "plan": {"type": "string"}
                },
                "required": ["plan"]
            },
            "response_model": "transaction",
            "auth_required": True,
            "roles": ["User", "PremiumUser", "Admin"]
        })

    api_schema = {
        "routes": routes
    }

    # 3. DB Schema
    tables = [
        {
            "name": "user",
            "columns": [
                {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
                {"name": "email", "type": "string", "constraints": ["UNIQUE", "NOT NULL"]},
                {"name": "password_hash", "type": "string", "constraints": ["NOT NULL"]},
                {"name": "role", "type": "string", "constraints": ["NOT NULL"]}
            ],
            "indexes": ["email"],
            "foreign_keys": []
        }
    ]
    
    # Add entities to table list
    if app_type == "crm":
        contact_columns = [
            {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
            {"name": "user_id", "type": "integer", "constraints": ["NOT NULL"]},
            {"name": "name", "type": "string", "constraints": ["NOT NULL"]},
            {"name": "email", "type": "string", "constraints": []}
        ]
        
        # DELIBERATE INCONSISTENCY INJECTION FOR COMPILER FLOW
        # The 'phone' column is missing from DB table but exists in the UI form fields and API schemas!
        if not inject_bug:
            contact_columns.append({"name": "phone", "type": "string", "constraints": []})
            
        tables.append({
            "name": "contact",
            "columns": contact_columns,
            "indexes": ["user_id"],
            "foreign_keys": [
                {"column": "user_id", "references": "user(id)"}
            ]
        })
        
    elif app_type == "task":
        task_columns = [
            {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
            {"name": "user_id", "type": "integer", "constraints": ["NOT NULL"]},
            {"name": "title", "type": "string", "constraints": ["NOT NULL"]},
            {"name": "description", "type": "string", "constraints": []}
        ]
        
        # DELIBERATE INCONSISTENCY INJECTION FOR COMPILER FLOW
        # The 'status' column is missing from DB table but exists in the UI and API!
        if not inject_bug:
            task_columns.append({"name": "status", "type": "string", "constraints": ["NOT NULL"]})
            
        tables.append({
            "name": "task",
            "columns": task_columns,
            "indexes": ["user_id"],
            "foreign_keys": [
                {"column": "user_id", "references": "user(id)"}
            ]
        })

    elif app_type == "ecommerce":
        tables.extend([
            {
                "name": "product",
                "columns": [
                    {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
                    {"name": "name", "type": "string", "constraints": ["NOT NULL"]},
                    {"name": "price", "type": "number", "constraints": ["NOT NULL"]},
                    {"name": "description", "type": "string", "constraints": []}
                ],
                "indexes": [],
                "foreign_keys": []
            },
            {
                "name": "order",
                "columns": [
                    {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
                    {"name": "user_id", "type": "integer", "constraints": ["NOT NULL"]},
                    {"name": "shipping_address", "type": "string", "constraints": ["NOT NULL"]},
                    {"name": "total", "type": "number", "constraints": ["NOT NULL"]}
                ],
                "indexes": ["user_id"],
                "foreign_keys": [
                    {"column": "user_id", "references": "user(id)"}
                ]
            }
        ])
    elif app_type == "inventory":
        tables.append({
            "name": "inventory_item",
            "columns": [
                {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
                {"name": "name", "type": "string", "constraints": ["NOT NULL"]},
                {"name": "quantity", "type": "integer", "constraints": ["NOT NULL"]}
            ],
            "indexes": [],
            "foreign_keys": []
        })
    elif app_type == "content":
        tables.append({
            "name": "post",
            "columns": [
                {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
                {"name": "user_id", "type": "integer", "constraints": ["NOT NULL"]},
                {"name": "title", "type": "string", "constraints": ["NOT NULL"]},
                {"name": "content", "type": "string", "constraints": ["NOT NULL"]},
                {"name": "category", "type": "string", "constraints": []}
            ],
            "indexes": ["user_id"],
            "foreign_keys": [
                {"column": "user_id", "references": "user(id)"}
            ]
        })

    # Billing transaction records
    if "/billing" in pages:
        tables.append({
            "name": "transaction",
            "columns": [
                {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
                {"name": "user_id", "type": "integer", "constraints": ["NOT NULL"]},
                {"name": "plan", "type": "string", "constraints": ["NOT NULL"]},
                {"name": "amount", "type": "number", "constraints": ["NOT NULL"]},
                {"name": "timestamp", "type": "string", "constraints": ["NOT NULL"]}
            ],
            "indexes": ["user_id"],
            "foreign_keys": [
                {"column": "user_id", "references": "user(id)"}
            ]
        })

    db_schema = {
        "tables": tables
    }

    # 4. Auth Rules Schema
    auth_rules = {
        "strategy": "jwt",
        "jwt_config": {
            "secret": "ai_app_compiler_super_secret_key_2026",
            "algorithm": "HS256",
            "expire_minutes": 60
        },
        "role_hierarchy": {
            "Admin": ["Manager", "PremiumUser", "User"],
            "Manager": ["User"],
            "PremiumUser": ["User"],
            "User": []
        },
        "permission_map": permissions
    }

    # 5. Business Logic Schema
    biz_rules = []
    
    if app_type == "crm":
        biz_rules.append({
            "trigger": "create_contact",
            "condition": "current_user.role == 'User' and db.count('contact', user_id=current_user.id) >= 5",
            "action": "reject",
            "error_response": "Standard free users are restricted to 5 contacts. Please upgrade to a Premium Plan for unlimited contacts."
        })
    elif app_type == "task":
        biz_rules.append({
            "trigger": "create_task",
            "condition": "current_user.role == 'User' and db.count('task', user_id=current_user.id) >= 10",
            "action": "reject",
            "error_response": "Free tier permits max 10 tasks. Upgrade required."
        })
    elif app_type == "ecommerce":
        biz_rules.append({
            "trigger": "create_order",
            "condition": "order.total > 500 and current_user.role != 'PremiumUser'",
            "action": "flag_review",
            "error_response": "Orders over $500 require Premium account authorization or manager review."
        })
    elif app_type == "content":
        biz_rules.append({
            "trigger": "create_post",
            "condition": "current_user.role == 'User'",
            "action": "reject",
            "error_response": "Standard users can only view posts. Authorship is reserved for Premium users and Admins."
        })

    biz_logic = {
        "rules": biz_rules
    }

    return {
        "ui_schema": ui_schema,
        "api_schema": api_schema,
        "db_schema": db_schema,
        "auth_rules": auth_rules,
        "biz_logic": biz_logic
    }

if __name__ == "__main__":
    blueprint = {
        "entities": ["user", "contact"],
        "pages": ["/login", "/register", "/dashboard", "/contacts", "/admin/analytics", "/billing"],
        "permissions": {"User": ["view_dashboard", "view_contacts", "create_contacts"], "Admin": ["manage_users", "view_analytics"]}
    }
    print(json.dumps(generate_schemas(blueprint, inject_bug=True), indent=2))
