import json

def validate_schemas(schemas: dict) -> dict:
    """
    Stage 4: Validation Engine
    Runs structural checks and cross-layer consistency validation.
    Returns ValidationReport.
    """
    ui_schema = schemas.get("ui_schema", {})
    api_schema = schemas.get("api_schema", {})
    db_schema = schemas.get("db_schema", {})
    auth_rules = schemas.get("auth_rules", {})
    biz_logic = schemas.get("biz_logic", {})

    errors = []
    warnings = []
    cross_layer_issues = []

    # 1. Helper to find a table by name
    tables = db_schema.get("tables", [])
    def find_table(name):
        for t in tables:
            if t["name"] == name:
                return t
        return None

    # Map API response/request targets to DB tables
    route_table_map = {
        "/api/v1/contacts": "contact",
        "/api/v1/tasks": "task",
        "/api/v1/orders": "order",
        "/api/v1/products": "product",
        "/api/v1/posts": "post",
        "/api/v1/inventory/adjust": "inventory_item",
        "/api/v1/inventory": "inventory_item",
        "/api/v1/billing/checkout": "transaction"
    }

    # 2. Check: DB Field Existence (Cross-Layer API -> DB)
    routes = api_schema.get("routes", [])
    for route in routes:
        path = route.get("path")
        method = route.get("method")
        req_model = route.get("request_model")
        
        # Check properties against corresponding table
        table_name = route_table_map.get(path)
        if table_name and req_model and "properties" in req_model:
            table = find_table(table_name)
            if table:
                db_cols = [c["name"] for c in table.get("columns", [])]
                for prop_name in req_model["properties"].keys():
                    # Handle common mappings/virtual fields
                    if prop_name in ["password", "card_number", "quantity_delta", "item_id", "plan"]:
                        # e.g., 'password' maps to 'password_hash' in user table, card_number is not stored directly, etc.
                        continue
                        
                    if prop_name not in db_cols:
                        # Missing field in DB!
                        loc = f"db_schema.tables.{table_name}.{prop_name}"
                        err_msg = f"Field '{prop_name}' is declared in API request model for route '{method} {path}' but is missing in DB table '{table_name}' columns."
                        errors.append({
                            "type": "field_missing",
                            "location": loc,
                            "detail": err_msg
                        })
                        cross_layer_issues.append({
                            "source_layer": "api_schema",
                            "target_layer": "db_schema",
                            "issue": f"API route '{method} {path}' requires field '{prop_name}' which has no matching database column in '{table_name}' table."
                        })
            else:
                # Table not found in DB
                errors.append({
                    "type": "table_missing",
                    "location": f"db_schema.tables.{table_name}",
                    "detail": f"API route '{path}' maps to DB table '{table_name}', but this table does not exist in DB Schema."
                })
                cross_layer_issues.append({
                    "source_layer": "api_schema",
                    "target_layer": "db_schema",
                    "issue": f"API references table '{table_name}' which is missing in DB."
                })

    # 3. Check: API Coverage (Cross-Layer UI -> API)
    components = ui_schema.get("components", [])
    for comp in components:
        if comp.get("type") == "Form":
            target = comp.get("submit_target")
            # Verify if this POST target exists in API schema
            api_found = False
            for route in routes:
                if route.get("path") == target and route.get("method") == "POST":
                    api_found = True
                    break
            
            if not api_found:
                errors.append({
                    "type": "api_endpoint_missing",
                    "location": f"ui_schema.components.{comp['name']}.submit_target",
                    "detail": f"UI Form '{comp['name']}' submits to '{target}', but no POST endpoint matches this path in API Schema."
                })
                cross_layer_issues.append({
                    "source_layer": "ui_schema",
                    "target_layer": "api_schema",
                    "issue": f"UI component '{comp['name']}' references submit target '{target}' not implemented in API Schema."
                })

    # 4. Check: Role Integrity (Cross-Layer API -> Auth / System Design Roles)
    declared_roles = list(auth_rules.get("permission_map", {}).keys())
    for route in routes:
        route_roles = route.get("roles", [])
        for role in route_roles:
            if role not in declared_roles:
                errors.append({
                    "type": "invalid_role",
                    "location": f"api_schema.routes.{route['path']}.roles",
                    "detail": f"API route '{route['path']}' restricts access to role '{role}', but '{role}' is not registered in Auth rules."
                })
                cross_layer_issues.append({
                    "source_layer": "api_schema",
                    "target_layer": "auth_rules",
                    "issue": f"Role '{role}' is referenced by API access rules but undefined in system roles."
                })

    # 5. Check: Business Logic Events
    rules = biz_logic.get("rules", [])
    for rule in rules:
        trigger = rule.get("trigger")
        # trigger format e.g. "create_contact", "create_task"
        # Check if there is an API route that can trigger this event
        action_verb = trigger.split("_")[0] if "_" in trigger else ""
        entity_name = "_".join(trigger.split("_")[1:]) if "_" in trigger else ""
        
        route_found = False
        for route in routes:
            path = route.get("path")
            method = route.get("method")
            mapped_table = route_table_map.get(path)
            
            if method == "POST" and action_verb == "create" and mapped_table == entity_name:
                route_found = True
                break
            elif method == "DELETE" and action_verb == "delete" and mapped_table == entity_name:
                route_found = True
                break
                
        if not route_found:
            warnings.append({
                "type": "untriggerable_business_rule",
                "location": f"biz_logic.rules.{trigger}",
                "suggestion": f"Business rule trigger '{trigger}' has no matching POST/DELETE endpoint on entity '{entity_name}'."
            })

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "cross_layer_issues": cross_layer_issues
    }

if __name__ == "__main__":
    from schema_generator import generate_schemas
    blueprint = {
        "entities": ["user", "contact"],
        "pages": ["/login", "/register", "/dashboard", "/contacts"],
        "permissions": {"User": ["view_dashboard", "view_contacts", "create_contacts"], "Admin": ["manage_users"]}
    }
    # Test with bug injected (should be invalid)
    schemas_with_bug = generate_schemas(blueprint, inject_bug=True)
    report_bug = validate_schemas(schemas_with_bug)
    print("WITH BUG:")
    print(json.dumps(report_bug, indent=2))
    
    # Test with bug resolved (should be valid)
    schemas_clean = generate_schemas(blueprint, inject_bug=False)
    report_clean = validate_schemas(schemas_clean)
    print("\nWITHOUT BUG:")
    print(json.dumps(report_clean, indent=2))
