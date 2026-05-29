import re
import json

def extract_intent(prompt: str) -> dict:
    """
    Stage 1: Intent Extraction
    Converts raw natural language prompt into IntentIR JSON structure.
    """
    # Normalize input
    text = prompt.lower()
    
    # 1. Classify App Type
    app_type = "SaaS Application"
    if any(k in text for k in ["crm", "contact", "lead", "deal", "customer"]):
        app_type = "Customer Relationship Management (CRM)"
    elif any(k in text for k in ["task", "todo", "kanban", "project"]):
        app_type = "Task Management Portal"
    elif any(k in text for k in ["store", "shop", "ecommerce", "cart", "product", "checkout", "order"]):
        app_type = "E-Commerce Storefront"
    elif any(k in text for k in ["inventory", "stock", "warehouse", "item"]):
        app_type = "Inventory Management System"
    elif any(k in text for k in ["blog", "post", "article", "news", "content"]):
        app_type = "Content Management System (CMS)"
    
    # 2. Extract Features (with normalization)
    features = []
    
    # Core features check
    if any(k in text for k in ["login", "register", "auth", "signin", "signup", "user", "password", "session"]):
        features.append("authentication")
    else:
        # Implicitly add authentication if roles or premium plan are mentioned
        if any(k in text for k in ["admin", "manager", "role", "premium"]):
            features.append("authentication")
            
    if any(k in text for k in ["dashboard", "overview", "home", "stats"]):
        features.append("dashboard")
        
    if any(k in text for k in ["payment", "checkout", "stripe", "billing", "premium", "price", "pay", "subscribe"]):
        features.append("billing")
        
    if any(k in text for k in ["analytics", "stats", "charts", "metrics", "reports", "report"]):
        features.append("analytics")
        
    # App-specific features
    if "crm" in app_type.lower():
        features.extend(["contact_management", "sales_pipeline"])
    elif "task" in app_type.lower():
        features.extend(["task_tracking", "project_boards"])
    elif "e-commerce" in app_type.lower():
        features.extend(["product_catalog", "shopping_cart", "order_processing"])
    elif "inventory" in app_type.lower():
        features.extend(["stock_tracking", "warehouse_management"])
    elif "content" in app_type.lower():
        features.extend(["article_publishing", "comments_section"])
        
    # Remove duplicates
    features = list(dict.fromkeys(features))
    
    # 3. Extract Roles
    roles = ["User"] # Base role always exists
    if "admin" in text or "administrator" in text:
        roles.append("Admin")
    if "manager" in text or "coordinator" in text:
        roles.append("Manager")
    if "premium" in text or "paid" in text or "billing" in features:
        roles.append("PremiumUser")
    roles = list(dict.fromkeys(roles))
    
    # 4. Detect Ambiguities, Assumptions and Missing Requirements
    ambiguities = []
    assumptions = []
    missing_requirements = []
    
    # Check for authentication details
    if "authentication" in features and not any(k in text for k in ["password", "jwt", "oauth", "mfa"]):
        ambiguities.append("Authentication mechanism not specified (e.g. JWT, Session, OAuth).")
        assumptions.append("Using JWT-based token authentication with secure password hashing.")
        
    # Check for database persistence
    if not any(k in text for k in ["sqlite", "postgres", "mysql", "database", "db"]):
        ambiguities.append("Database storage engine not explicitly chosen.")
        assumptions.append("Compiling into SQLite for single-file, serverless relational persistence.")
        
    # Check for role-based permissions
    if len(roles) > 1:
        if not any(k in text for k in ["permission", "access control", "rbac", "allow", "restrict"]):
            ambiguities.append("Specific access control permissions for roles are undefined.")
            assumptions.append("Default RBAC rules applied: Admin has full read/write, Manager has write/edit, User has read-write on owned resources, PremiumUser gets access to billing-restricted features.")
            
    # Check for payments
    if "billing" in features:
        if not any(k in text for k in ["stripe", "paypal", "gateway", "card"]):
            ambiguities.append("Payment processor gateway not specified.")
            assumptions.append("Simulating a Stripe Checkout flow with sandbox-mocked transaction receipts.")
            
    # App-specific missing requirements
    if "crm" in app_type.lower():
        missing_requirements.append("Lead lifecycle stages (e.g. New, Contacted, Qualified, Closed) are unstated. Defaults injected.")
    elif "task" in app_type.lower():
        missing_requirements.append("Task statuses (e.g. Todo, In Progress, Done) not specified. Defaults injected.")
    elif "e-commerce" in app_type.lower():
        missing_requirements.append("Checkout fields and currency details not specified. Using USD and basic shipping inputs.")
        
    # Classifier classification
    classification = "CLEAR"
    if len(ambiguities) > 2:
        classification = "AMBIGUOUS"
    elif any(k in text for k in ["all users are admin", "admin has no access"]):
        classification = "CONFLICTING"
    elif len(text.strip().split()) < 8:
        classification = "VAGUE"

    return {
        "classification": classification,
        "intent_ir": {
            "app_type": app_type,
            "features": features,
            "roles": roles,
            "ambiguities": ambiguities,
            "assumptions": assumptions,
            "missing_requirements": missing_requirements
        }
    }

if __name__ == "__main__":
    test_prompt = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    print(json.dumps(extract_intent(test_prompt), indent=2))
