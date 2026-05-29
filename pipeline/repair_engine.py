import copy
import json

def repair_schemas(schemas: dict, report: dict, retry_count: int = 1) -> tuple[dict, dict]:
    """
    Stage 5: Repair Engine
    Surgically repairs inconsistencies listed in the ValidationReport.
    Avoids full regeneration of schemas by performing precise JSON patches.
    """
    # Create deep copies to prevent side effects
    patched_schemas = copy.deepcopy(schemas)
    errors = report.get("errors", [])
    
    repairs_logged = []
    
    for i, err in enumerate(errors):
        err_type = err.get("type")
        location = err.get("location", "")
        detail = err.get("detail", "")
        
        # Scenario 1: Missing column in DB schema table
        if err_type == "field_missing" and location.startswith("db_schema.tables."):
            # Parse location: db_schema.tables.<table_name>.<column_name>
            parts = location.split(".")
            if len(parts) >= 4:
                table_name = parts[2]
                col_name = parts[3]
                
                # Locate the table in patched schemas
                tables = patched_schemas.get("db_schema", {}).get("tables", [])
                for table in tables:
                    if table["name"] == table_name:
                        before_cols = copy.deepcopy(table["columns"])
                        
                        # Surgically inject the missing column
                        new_col = {"name": col_name, "type": "string", "constraints": []}
                        
                        # If task table, status should be NOT NULL for business logic
                        if table_name == "task" and col_name == "status":
                            new_col["constraints"] = ["NOT NULL"]
                            
                        table["columns"].append(new_col)
                        
                        repairs_logged.append({
                            "error_ref": f"ValidationReport.errors[{i}]",
                            "strategy": "patch",
                            "before": f"Table '{table_name}' columns: {[c['name'] for c in before_cols]}",
                            "after": f"Table '{table_name}' columns: {[c['name'] for c in table['columns']]}",
                            "rationale": f"Surgically added missing column '{col_name}' to table '{table_name}' to satisfy API contract mapping requirements."
                        })
                        break
                        
        # Scenario 2: API Endpoint missing from API Schema
        elif err_type == "api_endpoint_missing" and location.startswith("ui_schema.components."):
            # Form UI refers to a POST path that doesn't exist. Add the API route.
            submit_target = err.get("detail").split("'")[-2] # Extract route path
            routes = patched_schemas.get("api_schema", {}).get("routes", [])
            
            before_routes_count = len(routes)
            # Add basic POST endpoint
            new_route = {
                "path": submit_target,
                "method": "POST",
                "request_model": {
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                },
                "response_model": "dynamic_status",
                "auth_required": True,
                "roles": ["User", "Admin"]
            }
            routes.append(new_route)
            
            repairs_logged.append({
                "error_ref": f"ValidationReport.errors[{i}]",
                "strategy": "patch",
                "before": f"API Routes count: {before_routes_count}",
                "after": f"API Routes count: {len(routes)} (added POST {submit_target})",
                "rationale": f"Surgically added missing API POST endpoint '{submit_target}' to satisfy UI form submission requests."
            })
            
        # Scenario 3: Undeclared Role in API Route
        elif err_type == "invalid_role" and location.startswith("api_schema.routes."):
            # Add role to Auth rules permission map
            role_name = err.get("detail").split("'")[-2]
            permission_map = patched_schemas.get("auth_rules", {}).get("permission_map", {})
            
            before_roles = list(permission_map.keys())
            if role_name not in permission_map:
                permission_map[role_name] = ["view_dashboard"]
                
            repairs_logged.append({
                "error_ref": f"ValidationReport.errors[{i}]",
                "strategy": "patch",
                "before": f"Auth Roles: {before_roles}",
                "after": f"Auth Roles: {list(permission_map.keys())}",
                "rationale": f"Registered undefined role '{role_name}' into Auth permission map with baseline permissions."
            })

    repair_log = {
        "repairs": repairs_logged,
        "retry_count": retry_count,
        "max_retries_hit": retry_count >= 3
    }
    
    return patched_schemas, repair_log

if __name__ == "__main__":
    from schema_generator import generate_schemas
    from validator import validate_schemas
    
    blueprint = {
        "entities": ["user", "contact"],
        "pages": ["/login", "/register", "/dashboard", "/contacts"],
        "permissions": {"User": ["view_dashboard", "view_contacts", "create_contacts"], "Admin": ["manage_users"]}
    }
    schemas = generate_schemas(blueprint, inject_bug=True)
    report = validate_schemas(schemas)
    
    print("Pre-repair Validation valid:", report["valid"])
    
    patched_schemas, log = repair_schemas(schemas, report)
    print("\nRepair Log:")
    print(json.dumps(log, indent=2))
    
    post_report = validate_schemas(patched_schemas)
    print("\nPost-repair Validation valid:", post_report["valid"])
