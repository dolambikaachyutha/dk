import streamlit as st
import datetime
from db.db_utils import add_listing
from engine.material_analyzer import analyze_listing
from engine.price_engine import get_price
from engine.carbon_engine import carbon_saved

# Ensure user is logged in
if not st.session_state.user or st.session_state.user["role"] != "supplier":
    st.warning("Please log in as a Supplier to view this page.")
    st.switch_page("pages/supplier_login.py")
    st.stop()

user = st.session_state.user

st.title("➕ List Secondary Raw Material")
st.caption("Create a new marketplace listing manually or accelerate listing creation using AI text parsing.")

# Initialize autofill session state
if "autofill" not in st.session_state:
    st.session_state.autofill = {
        "material": "Wood Waste",
        "quantity": 100.0,
        "unit": "kg",
        "price": 10.0,
        "location": "",
        "condition": "Good",
        "expiry_days": 30,
        "description": ""
    }

# AI Smart Autofill Section
st.markdown("### 🪄 AI Smart Autofill")
with st.expander("Type a quick description to autofill the form below:", expanded=True):
    ai_desc = st.text_area(
        "Listing Description Draft",
        placeholder="e.g. We have about 350 kg of high-quality wood scraps from construction trimmings in our Bengaluru facility. Dry and in good condition. Expires in 45 days. Price 9 rupees.",
        key="ai_autofill_input"
    )
    if st.button("🪄 Parse Description with AI", use_container_width=True):
        if not ai_desc.strip():
            st.error("Please enter a description text first.")
        else:
            with st.spinner("AI parsing description and extracting details..."):
                try:
                    result = analyze_listing(ai_desc)
                    # Map material types
                    extracted_mat = result.get("material_type", "wood").lower()
                    mat_map = {
                        "wood": "Wood Waste",
                        "cotton": "Cotton Waste",
                        "fabric": "Textile Waste",
                        "plastic": "Plastic Waste",
                        "paper": "Paper Waste",
                        "metal": "Metal Scrap",
                        "organic": "Organic Waste"
                    }
                    mapped_mat = mat_map.get(extracted_mat, "Wood Waste")
                    
                    # Estimate price using pricing engine
                    suggested_price = get_price(extracted_mat)
                    
                    # Try to extract location using regex or defaults
                    import re
                    loc_match = re.search(r"in\s+([A-Za-z\s]+)(?:facility|warehouse|office|city|\.|$)", ai_desc, re.IGNORECASE)
                    extracted_loc = loc_match.group(1).strip() if loc_match else ""
                    
                    st.session_state.autofill = {
                        "material": mapped_mat,
                        "quantity": float(result.get("quantity", 100.0)),
                        "unit": result.get("unit", "kg"),
                        "price": float(result.get("price", suggested_price)),
                        "location": extracted_loc,
                        "condition": result.get("condition", "Good").title(),
                        "expiry_days": int(result.get("lifetime_days", 30)),
                        "description": result.get("summary", ai_desc)
                    }
                    st.success("Form fields successfully extracted! Review the form below and publish.")
                    st.rerun()
                except Exception as e:
                    st.error(f"AI Autofill parsing encountered an error: {e}")

st.divider()

# Standard Form
st.markdown("### 📝 Listing Parameters")
with st.form("add_material_form"):
    material = st.selectbox(
        "Material Category",
        ["Wood Waste", "Cotton Waste", "Textile Waste", "Plastic Waste", "Paper Waste", "Metal Scrap", "Organic Waste"],
        index=["Wood Waste", "Cotton Waste", "Textile Waste", "Plastic Waste", "Paper Waste", "Metal Scrap", "Organic Waste"].index(st.session_state.autofill["material"])
    )
    
    col_qty, col_unit = st.columns(2)
    with col_qty:
        quantity = st.number_input("Quantity", min_value=1.0, value=st.session_state.autofill["quantity"])
    with col_unit:
        unit = st.selectbox("Measurement Unit", ["kg", "tons", "units"], index=["kg", "tons", "units"].index(st.session_state.autofill["unit"].lower() if st.session_state.autofill["unit"].lower() in ["kg", "tons", "units"] else "kg"))
        
    col_price, col_loc = st.columns(2)
    with col_price:
        price_per_kg = st.number_input("Asking Price (₹ / kg)", min_value=0.1, value=st.session_state.autofill["price"])
    with col_loc:
        location = st.text_input("Source Facility Location (City)", value=st.session_state.autofill["location"], placeholder="e.g. Bengaluru")
        
    condition = st.selectbox(
        "Material Quality / Condition",
        ["Excellent", "Good", "Fair", "Poor"],
        index=["Excellent", "Good", "Fair", "Poor"].index(st.session_state.autofill["condition"])
    )
    
    # Expiry Date Selector
    expiry_date = st.date_input(
        "Listing Expiry Date (Lifetime / Shelf-life)",
        value=datetime.date.today() + datetime.timedelta(days=int(st.session_state.autofill.get("expiry_days", 30)))
    )
    
    description = st.text_area("Detailed Description / Material specifications", value=st.session_state.autofill["description"])
    
    submit_btn = st.form_submit_button("📢 Publish Material Listing", use_container_width=True)

if submit_btn:
    if not location.strip():
        st.error("Please provide your facility's location.")
    elif expiry_date < datetime.date.today():
        st.error("Expiry date cannot be in the past.")
    else:
        # Calculate carbon saved dynamically
        cat_key = material.split(" ")[0].lower()
        
        qty_kg = quantity
        if unit == "tons":
            qty_kg = quantity * 1000.0
            
        saved_carbon = carbon_saved(cat_key, qty_kg) / 1000.0  # Express in metric tons
        
        # Save listing to database
        add_listing(
            supplier_id=user["id"],
            material=material,
            quantity=quantity,
            unit=unit,
            price_per_kg=price_per_kg,
            location=location,
            condition=condition.lower(),
            description=description,
            carbon_saved=saved_carbon,
            expiry_date=expiry_date.strftime("%Y-%m-%d")
        )
        
        # Reset autofill state
        st.session_state.autofill = {
            "material": "Wood Waste",
            "quantity": 100.0,
            "unit": "kg",
            "price": 10.0,
            "location": "",
            "condition": "Good",
            "expiry_days": 30,
            "description": ""
        }
        
        st.success("Successfully published waste lot! Listing is now active on the Marketplace.")
        st.toast("Listing Published!", icon="📢")
        st.switch_page("pages/my_listings.py")
