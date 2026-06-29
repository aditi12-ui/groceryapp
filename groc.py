import mysql.connector
import streamlit as st


# Secure database connection setup
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="kafka-37918310-aditysh06-d6a0.d.aivencloud.com",
            user="root",  # Your MySQL user
            password="mysql@123",  # Your MySQL password
            database="grocery_booking_db",
        )
    except mysql.connector.Error as err:
        st.error(f"Database Connection Error: {err}")
        return None


# Helper function to query backend items
def fetch_inventory():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventory WHERE available_stock > 0")
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        return items
    return []


# --- Web Layout Design ---
st.set_page_config(page_title="Local Grocery Booking", layout="wide")
st.title("🛒 Local General Store Grocery Booking Portal")
st.markdown("Book your daily essentials online and pick them up at the counter!")

# Create a multi-tab view website layout
tab_browse, tab_admin = st.tabs(
    ["🛍️ Browse & Book Groceries", "📊 Store Admin Dashboard"]
)

# ----------------- TAB 1: CUSTOMER VIEW -----------------
with tab_browse:
    st.subheader("Step 1: Select a Local General Store")

    inventory_data = fetch_inventory()

    if not inventory_data:
        st.warning("No items are currently available in the database.")
    else:
        # Extract unique store names for filtering dropdown
        stores = sorted(list(set([item["store_name"] for item in inventory_data])))
        selected_store = st.selectbox("Choose a store near you:", stores)

        # Filter database records matching user store choice
        filtered_items = [
            item for item in inventory_data if item["store_name"] == selected_store
        ]

        st.subheader(f"Step 2: Available Stock at {selected_store}")

        # Display items nicely inside responsive rows
        for item in filtered_items:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
            with col1:
                st.markdown(f"**{item['item_name']}** ({item['category']})")
            with col2:
                st.markdown(f"Price: ${item['price']:.2f}")
            with col3:
                st.markdown(f"Stock: {item['available_stock']} units left")
            with col4:
                # Unique button key using item ID prevents rendering errors
                if st.button(f"Select {item['item_name']}", key=f"btn_{item['item_id']}"):
                    st.session_state["selected_item_details"] = item

        # Booking Checkout Panel block
        if "selected_item_details" in st.session_state:
            target = st.session_state["selected_item_details"]
            st.write("---")
            st.subheader(f"Step 3: Complete Booking for {target['item_name']}")

            # Customer information form fields
            cust_name = st.text_input("Your Full Name")
            cust_phone = st.text_input("Your Phone Number")
            quantity = st.number_input(
                "Quantity to Book", min_value=1, max_value=target["available_stock"]
            )

            total_cost = target["price"] * quantity
            st.info(f"💰 Total Amount to Pay at Store: **${total_cost:.2f}**")

            if st.button("Confirm Order Booking"):
                if not cust_name or not cust_phone:
                    st.error("Please fill in your Name and Contact Phone details!")
                else:
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        # 1. Update the inventory table stock level
                        update_query = "UPDATE inventory SET available_stock = available_stock - %s WHERE item_id = %s"
                        cursor.execute(update_query, (quantity, target["item_id"]))

                        # 2. Record the fresh customer booking
                        booking_query = """
                            INSERT INTO bookings (customer_name, customer_phone, store_name, item_id, quantity_booked, total_price)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(
                            booking_query,
                            (
                                cust_name,
                                cust_phone,
                                selected_store,
                                target["item_id"],
                                quantity,
                                total_cost,
                            ),
                        )

                        conn.commit()
                        cursor.close()
                        conn.close()

                        st.success(
                            f"🎉 Success! Your booking ID has been registered. Please pick up your items at {selected_store}."
                        )
                        del st.session_state["selected_item_details"]
                        st.rerun()

# ----------------- TAB 2: STORE OWNER VIEW -----------------
with tab_admin:
    st.subheader("📋 Incoming Store Bookings Logs")
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.booking_id, b.customer_name, b.customer_phone, b.store_name, 
                   i.item_name, b.quantity_booked, b.total_price, b.booking_date 
            FROM bookings b 
            LEFT JOIN inventory i ON b.item_id = i.item_id
            ORDER BY b.booking_date DESC
        """)
        all_bookings = cursor.fetchall()
        cursor.close()
        conn.close()

        if all_bookings:
            st.dataframe(all_bookings, use_container_width=True)
        else:
            st.info("No bookings have been made yet by clients.")
