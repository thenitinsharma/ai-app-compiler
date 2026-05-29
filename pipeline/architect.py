import json

def design_system(intent_ir: dict) -> dict:
    """
    Stage 2: System Design
    Builds the SystemBlueprint based on IntentIR extracted features and roles.
    """
    app_type = intent_ir.get("app_type", "SaaS Application")
    features = intent_ir.get("features", [])
    roles = intent_ir.get("roles", ["User"])
    
    entities = ["user"]
    pages = ["/login", "/register", "/dashboard"]
    modules = ["auth", "dashboard"]
    flows = [
        {
            "name": "User Authentication",
            "steps": [
                "User enters email and password on /login or /register page",
                "Frontend validates input format locally",
                "Frontend submits POST request to /api/v1/auth/login or /api/v1/auth/register",
                "Backend checks credentials, hashes password, saves to DB, returns JWT token",
                "Frontend stores JWT in localStorage, redirects user to /dashboard"
            ]
        }
    ]
    relationships = []
    
    # App type specific extensions
    if "crm" in app_type.lower():
        entities.append("contact")
        pages.append("/contacts")
        modules.append("contacts")
        relationships.append({
            "from": "user",
            "to": "contact",
            "type": "one_to_many"
        })
        flows.append({
            "name": "Contact Management Flow",
            "steps": [
                "Authenticated user views list of contacts at /contacts page",
                "User clicks 'Add Contact' and fills out contact form modal",
                "Frontend submits contact data via POST /api/v1/contacts with JWT headers",
                "Backend validates fields, links contact to current user ID, and inserts into DB",
                "Backend returns status code 201 with saved contact",
                "Frontend refreshes contact table"
            ]
        })
    elif "task" in app_type.lower():
        entities.extend(["task", "project"])
        pages.extend(["/tasks", "/projects"])
        modules.extend(["tasks", "projects"])
        relationships.extend([
            {"from": "user", "to": "task", "type": "one_to_many"},
            {"from": "project", "to": "task", "type": "one_to_many"}
        ])
        flows.append({
            "name": "Task Kanban Operations Flow",
            "steps": [
                "User navigates to /tasks board view",
                "User clicks 'Create Task' button and inputs fields (title, description, status)",
                "Frontend posts task details to POST /api/v1/tasks",
                "Backend saves task record associated with creator and active project",
                "Frontend updates board state with new task item in 'todo' column"
            ]
        })
    elif "e-commerce" in app_type.lower():
        entities.extend(["product", "order"])
        pages.extend(["/products", "/cart", "/orders"])
        modules.extend(["products", "cart", "orders"])
        relationships.extend([
            {"from": "user", "to": "order", "type": "one_to_many"},
            {"from": "product", "to": "order", "type": "many_to_many"}
        ])
        flows.append({
            "name": "E-Commerce Checkout Flow",
            "steps": [
                "User browsing /products adds items to cart page",
                "User reviews cart contents and clicks 'Proceed to checkout'",
                "Frontend redirects to Stripe Mock Payment Checkout interface",
                "Upon success, frontend issues POST to /api/v1/orders with cart data",
                "Backend processes inventory updates, creates order record, returns success",
                "User views summary on /orders invoice screen"
            ]
        })
    elif "inventory" in app_type.lower():
        entities.extend(["item", "warehouse"])
        pages.extend(["/inventory", "/warehouses"])
        modules.extend(["inventory", "warehouses"])
        relationships.extend([
            {"from": "warehouse", "to": "item", "type": "one_to_many"}
        ])
        flows.append({
            "name": "Stock Level Adjustment Flow",
            "steps": [
                "Warehouse operator navigates to /inventory",
                "Operator selects stock item and enters positive/negative adjustment count",
                "Frontend submits PATCH request to /api/v1/inventory/{item_id}",
                "Backend updates stock tables and logs audit entry",
                "UI updates with real-time stock quantity indicator"
            ]
        })
    elif "content" in app_type.lower():
        entities.extend(["post", "comment"])
        pages.extend(["/posts", "/post-detail"])
        modules.extend(["posts", "comments"])
        relationships.extend([
            {"from": "user", "to": "post", "type": "one_to_many"},
            {"from": "post", "to": "comment", "type": "one_to_many"},
            {"from": "user", "to": "comment", "type": "one_to_many"}
        ])
        flows.append({
            "name": "Article Publishing Flow",
            "steps": [
                "Author logs in and enters article editing view",
                "Author completes text editor fields and hits publish",
                "Frontend sends payload via POST to /api/v1/posts",
                "Backend saves content, flags active status, and broadcasts to readers",
                "Author is redirected to live post layout"
            ]
        })
        
    # Billing features
    if "billing" in features:
        entities.append("transaction")
        pages.append("/billing")
        modules.append("billing")
        relationships.append({
            "from": "user",
            "to": "transaction",
            "type": "one_to_many"
        })
        flows.append({
            "name": "Premium Plan Subscription Flow",
            "steps": [
                "User clicks upgrade on /billing page",
                "User triggers checkout, submitting billing transaction",
                "API logs transaction, upgrades User role flag to PremiumUser",
                "Frontend unlocks billing-restricted areas"
            ]
        })
        
    # Analytics features
    if "analytics" in features:
        pages.append("/admin/analytics")
        modules.append("analytics")
        flows.append({
            "name": "Analytics Dashboard Rendering",
            "steps": [
                "Admin accesses /admin/analytics dashboard",
                "Frontend triggers GET /api/v1/analytics/overview request with admin token",
                "Backend runs aggregations across transactions, users, and app items",
                "Backend returns summary object",
                "Frontend charts total metrics graphically"
            ]
        })

    # Deduplicate lists
    entities = list(dict.fromkeys(entities))
    pages = list(dict.fromkeys(pages))
    modules = list(dict.fromkeys(modules))
    
    # 5. Define Permissions per Role
    permissions = {}
    for r in roles:
        role_lower = r.lower()
        role_permissions = ["view_dashboard"]
        
        # User permissions
        if r == "User":
            if "crm" in app_type.lower():
                role_permissions.extend(["view_contacts", "create_contacts", "edit_contacts"])
            elif "task" in app_type.lower():
                role_permissions.extend(["view_tasks", "create_tasks", "edit_tasks"])
            elif "e-commerce" in app_type.lower():
                role_permissions.extend(["view_products", "create_orders", "view_orders"])
            elif "inventory" in app_type.lower():
                role_permissions.extend(["view_items", "view_warehouses"])
            elif "content" in app_type.lower():
                role_permissions.extend(["view_posts", "create_comments"])
            
            if "billing" in features:
                role_permissions.extend(["create_billing_session", "view_billing"])
                
        # PremiumUser permissions
        elif r == "PremiumUser":
            if "crm" in app_type.lower():
                role_permissions.extend(["view_contacts", "create_contacts", "edit_contacts", "export_contacts"])
            elif "task" in app_type.lower():
                role_permissions.extend(["view_tasks", "create_tasks", "edit_tasks", "delete_tasks", "create_projects"])
            elif "e-commerce" in app_type.lower():
                role_permissions.extend(["view_products", "create_orders", "view_orders", "premium_discount"])
            elif "inventory" in app_type.lower():
                role_permissions.extend(["view_items", "view_warehouses", "create_adjustments"])
            elif "content" in app_type.lower():
                role_permissions.extend(["view_posts", "create_comments", "create_posts", "edit_posts"])
            
            if "billing" in features:
                role_permissions.extend(["create_billing_session", "view_billing", "view_invoices"])

        # Manager permissions
        elif r == "Manager":
            role_permissions.extend([
                "view_contacts", "create_contacts", "edit_contacts", "delete_contacts",
                "view_tasks", "create_tasks", "edit_tasks", "delete_tasks", "manage_projects",
                "view_items", "create_items", "edit_items", "adjust_stock",
                "view_posts", "create_posts", "edit_posts", "moderate_comments"
            ])
            
        # Admin permissions
        elif r == "Admin":
            # Admin has super access
            role_permissions.extend([
                "view_contacts", "create_contacts", "edit_contacts", "delete_contacts",
                "view_tasks", "create_tasks", "edit_tasks", "delete_tasks", "create_projects", "delete_projects",
                "view_products", "create_products", "edit_products", "delete_products", "view_orders",
                "view_items", "create_items", "edit_items", "delete_items", "adjust_stock", "manage_warehouses",
                "view_posts", "create_posts", "edit_posts", "delete_posts", "moderate_comments", "delete_comments",
                "manage_users", "view_analytics", "edit_settings"
            ])
            if "billing" in features:
                role_permissions.extend(["create_billing_session", "view_billing", "view_invoices", "refund_transaction", "view_financials"])
                
        # Clean permissions list to only keep relevant keys for active entities
        valid_verbs = ["view", "create", "edit", "delete", "manage", "moderate", "export", "access", "refund", "adjust"]
        filtered_perms = []
        for p in role_permissions:
            verb = p.split("_")[0]
            target = "_".join(p.split("_")[1:]) if "_" in p else ""
            
            # Keep general rules or rules matching active entities / modules / roles
            if not target:
                filtered_perms.append(p)
                continue
                
            is_valid_target = (
                target in entities or 
                target in modules or 
                target + "s" in entities or 
                target + "es" in entities or 
                any(target in page for page in pages) or
                target in ["settings", "users", "invoices", "financials", "billing_session", "premium_tools", "premium_discount"]
            )
            if is_valid_target:
                filtered_perms.append(p)
                
        permissions[r] = list(dict.fromkeys(filtered_perms))
        
    return {
        "entities": entities,
        "pages": pages,
        "modules": modules,
        "flows": flows,
        "relationships": relationships,
        "permissions": permissions
    }

if __name__ == "__main__":
    test_ir = {
        "app_type": "Customer Relationship Management (CRM)",
        "features": ["authentication", "dashboard", "billing", "analytics", "contact_management", "sales_pipeline"],
        "roles": ["User", "Admin", "PremiumUser"],
        "ambiguities": [],
        "assumptions": [],
        "missing_requirements": []
    }
    print(json.dumps(design_system(test_ir), indent=2))
