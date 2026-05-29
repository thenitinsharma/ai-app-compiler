# Schema Translator Utility
# Translates LLM-generated schemas (per REQUIRED_SCHEMA) to backend-compatible schemas expected by runtime_generator.py

import json

def translate_llm_schemas(llm_schemas: dict) -> dict:
    """
    Translates client-generated LLM schemas into the structures expected by pipeline/runtime_generator.py.
    """
    # 1. Retrieve raw LLM outputs
    intent = llm_schemas.get("intent", {})
    architecture = llm_schemas.get("architecture", {})
    ui_schema_llm = llm_schemas.get("ui_schema", {})
    api_schema_llm = llm_schemas.get("api_schema", {})
    db_schema_llm = llm_schemas.get("db_schema", {})
    auth_schema_llm = llm_schemas.get("auth_schema", {})

    app_type_raw = intent.get("app_type", "crm")
    app_type = "crm"
    if "task" in app_type_raw or any("task" in str(x).lower() for x in architecture.get("entities", [])):
        app_type = "task"
    elif "commerce" in app_type_raw or "shop" in app_type_raw or any("product" in str(x).lower() for x in architecture.get("entities", [])):
        app_type = "ecommerce"
    elif "inventory" in app_type_raw or any("item" in str(x).lower() for x in architecture.get("entities", [])):
        app_type = "inventory"
    elif "blog" in app_type_raw or "content" in app_type_raw or any("post" in str(x).lower() for x in architecture.get("entities", [])):
        app_type = "content"

    # --- 1. TRANSLATE DB SCHEMA ---
    tables = []
    # Always include the core 'user' table
    tables.append({
        "name": "user",
        "columns": [
            {"name": "id", "type": "integer", "constraints": ["PRIMARY KEY", "AUTOINCREMENT"]},
            {"name": "email", "type": "string", "constraints": ["UNIQUE", "NOT NULL"]},
            {"name": "password_hash", "type": "string", "constraints": ["NOT NULL"]},
            {"name": "role", "type": "string", "constraints": ["NOT NULL"]}
        ],
        "indexes": ["email"],
        "foreign_keys": []
    })

    # Read tables from LLM db_schema
    llm_tables = db_schema_llm.get("tables", [])
    llm_relations = db_schema_llm.get("relations", [])
    llm_indexes = db_schema_llm.get("indexes", [])

    def sanitize_table_name(name: str) -> str:
        name_lower = name.lower().strip()
        reserved = {
            "order": "orders",
            "group": "groups",
            "key": "keys",
            "select": "selects",
            "table": "tables",
            "index": "indexes"
        }
        return reserved.get(name_lower, name_lower)

    # Build mapping from old table names to sanitized table names
    table_name_map = {}
    for table in llm_tables:
        old_name = table.get("name", "").lower()
        if old_name:
            table_name_map[old_name] = sanitize_table_name(old_name)

    for table in llm_tables:
        old_t_name = table.get("name", "").lower()
        t_name = table_name_map.get(old_t_name, old_t_name)
        if not t_name or t_name == "user":
            continue

        columns = []
        p_key = table.get("primary_key", "id")
        
        for col in table.get("columns", []):
            c_name = col.get("name", "").lower()
            c_type = col.get("type", "string").lower()
            
            constraints = []
            if c_name == p_key:
                constraints.append("PRIMARY KEY")
                if c_type in ["integer", "int"]:
                    constraints.append("AUTOINCREMENT")
            else:
                if not col.get("nullable", True):
                    constraints.append("NOT NULL")
                if col.get("unique", False):
                    constraints.append("UNIQUE")
                    
            columns.append({
                "name": c_name,
                "type": c_type,
                "constraints": constraints
            })

        # Collect existing column names
        existing_cols = {c["name"] for c in columns}

        # Find foreign keys for this table from relations
        fks = []
        for rel in llm_relations:
            from_t = table_name_map.get(rel.get("from_table", "").lower(), rel.get("from_table", "").lower())
            to_t = table_name_map.get(rel.get("to_table", "").lower(), rel.get("to_table", "").lower())
            fk_col = rel.get("foreign_key", "").lower()
            if from_t == t_name and fk_col:
                fks.append({
                    "column": fk_col,
                    "references": f"{to_t}(id)"
                })
                # If foreign key column is missing in columns list, automatically inject it
                if fk_col not in existing_cols:
                    columns.append({
                        "name": fk_col,
                        "type": "integer",
                        "constraints": ["NOT NULL"]
                    })
                    existing_cols.add(fk_col)

        # Find indexes
        table_idxs = []
        for idx in llm_indexes:
            idx_t = table_name_map.get(idx.get("table", "").lower(), idx.get("table", "").lower())
            if idx_t == t_name:
                table_idxs.extend([c.lower() for c in idx.get("columns", [])])

        tables.append({
            "name": t_name,
            "columns": columns,
            "indexes": list(set(table_idxs)),
            "foreign_keys": fks
        })

    db_schema = {
        "tables": tables
    }

    # --- 2. TRANSLATE API SCHEMA ---
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

    llm_endpoints = api_schema_llm.get("endpoints", [])
    for ep in llm_endpoints:
        path = ep.get("path", "")
        method = ep.get("method", "GET").upper()
        raw_db_table = ep.get("db_table", "").lower()
        db_table = table_name_map.get(raw_db_table, raw_db_table)
        
        # Determine response model
        if method == "GET":
            response_model = f"{db_table}_list" if db_table else "dynamic_list"
        else:
            response_model = db_table if db_table else "dynamic_status"

        # Request model schema translation
        req_body = ep.get("request_body", {})
        request_model = None
        if req_body and isinstance(req_body, dict):
            properties = {}
            required = []
            for k, v in req_body.items():
                properties[k] = {"type": str(v)}
                required.append(k)
            request_model = {
                "properties": properties,
                "required": required
            }

        routes.append({
            "path": path,
            "method": method,
            "request_model": request_model,
            "response_model": response_model,
            "auth_required": ep.get("auth", True),
            "roles": ep.get("roles", ["User", "Admin"])
        })

    api_schema = {
        "routes": routes
    }

    # --- 3. TRANSLATE UI SCHEMA ---
    llm_pages = ui_schema_llm.get("pages", [])
    pages_list = [p.get("route", "") for p in llm_pages if p.get("route")]
    if not pages_list:
        pages_list = ["/login", "/register", "/dashboard"]
        if app_type == "crm":
            pages_list.append("/contacts")
        elif app_type == "task":
            pages_list.append("/tasks")

    components = []
    form_fields = {
        "email": {"type": "string", "label": "Email Address", "required": True},
        "password": {"type": "string", "label": "Password", "required": True}
    }

    llm_components = ui_schema_llm.get("components", [])
    for comp in llm_components:
        c_type = comp.get("type", "").lower()
        c_name = comp.get("name", "")
        api_dep = comp.get("api_dependency", "")
        
        if "form" in c_type or c_type == "form":
            # Form submission
            fields = []
            # Infer fields from form name/props or fallback to app defaults
            props = comp.get("props", {})
            if "fields" in props:
                fields = props["fields"]
            elif app_type == "crm" and "contact" in c_name.lower():
                fields = ["name", "email", "phone"]
                form_fields.update({
                    "name": {"type": "string", "label": "Full Name", "required": True},
                    "phone": {"type": "string", "label": "Phone Number", "required": False}
                })
            elif app_type == "task" and "task" in c_name.lower():
                fields = ["title", "description", "status"]
                form_fields.update({
                    "title": {"type": "string", "label": "Task Title", "required": True},
                    "description": {"type": "string", "label": "Description", "required": False},
                    "status": {"type": "string", "label": "Status", "required": True}
                })
            else:
                fields = list(props.keys()) if props else ["name"]
                for f in fields:
                    if f not in form_fields:
                        form_fields[f] = {"type": "string", "label": f.capitalize(), "required": True}

            components.append({
                "name": c_name,
                "type": "Form",
                "fields": fields,
                "submit_target": api_dep
            })
        else:
            components.append({
                "name": c_name,
                "type": comp.get("type", "Card"),
                "api_dependency": api_dep
            })

    # Render primary navigation
    llm_nav = ui_schema_llm.get("navigation", {})
    navigation_list = [
        {"label": "Dashboard", "path": "/dashboard", "icon": "Home"}
    ]
    
    # Add navigation items based on pages
    for route in pages_list:
        if route in ["/login", "/register", "/dashboard"]:
            continue
        label = route.replace("/", "").capitalize()
        icon = "Folder"
        if "contact" in route.lower():
            icon = "Users"
            label = "Contacts"
        elif "task" in route.lower():
            icon = "CheckSquare"
            label = "Tasks"
        elif "product" in route.lower():
            icon = "ShoppingBag"
            label = "Products"
        elif "order" in route.lower():
            icon = "Receipt"
            label = "Orders"
        elif "inventory" in route.lower():
            icon = "Archive"
            label = "Inventory"
        elif "post" in route.lower():
            icon = "BookOpen"
            label = "Articles"
        elif "billing" in route.lower():
            icon = "CreditCard"
            label = "Billing"
        elif "analytics" in route.lower():
            icon = "TrendingUp"
            label = "Analytics"

        navigation_list.append({
            "label": label,
            "path": route,
            "icon": icon
        })

    ui_schema = {
        "pages": pages_list,
        "components": components,
        "form_fields": form_fields,
        "navigation": navigation_list
    }

    # --- 4. TRANSLATE AUTH RULES ---
    # Construct permission map from LLM's permissions schema
    permission_map = {
        "Admin": ["view_dashboard", "manage_users"],
        "Manager": ["view_dashboard"],
        "PremiumUser": ["view_dashboard"],
        "User": ["view_dashboard"]
    }

    llm_perms = auth_schema_llm.get("permissions", [])
    for perm in llm_perms:
        res = perm.get("resource", "")
        act = perm.get("action", "")
        perm_roles = perm.get("roles", [])
        
        perm_str = f"{act}_{res}"
        for role in perm_roles:
            if role in permission_map:
                permission_map[role].append(perm_str)
            else:
                permission_map[role] = ["view_dashboard", perm_str]

    # Map architecture role_permissions if permission_map is sparse
    if len(llm_perms) == 0:
        arch_perms = architecture.get("role_permissions", {})
        for role, rules in arch_perms.items():
            r_name = role.capitalize()
            role_p = ["view_dashboard"]
            for can_do in rules.get("can", []):
                # e.g., 'create contact' -> 'create_contacts'
                p_normalized = can_do.lower().replace(" ", "_")
                if not p_normalized.endswith("s") and p_normalized.split("_")[-1] in ["contact", "task", "post", "order", "product"]:
                    p_normalized += "s"
                role_p.append(p_normalized)
            permission_map[r_name] = list(set(role_p))

    # Standard hierarchies
    auth_rules = {
        "strategy": auth_schema_llm.get("strategy", "jwt"),
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
        "permission_map": permission_map
    }

    # --- 5. TRANSLATE BUSINESS LOGIC ---
    biz_rules = []
    # Build standard billing/restriction rule if applicable
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
