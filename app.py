import streamlit as st
from database import db
from components import render_entry_form, render_record_card
from auth import init_auth, login_form, logout

# Initialize authentication
init_auth()

# Check authentication
if not login_form():
    st.stop()

# Initialize database tables
db.create_tables()

st.set_page_config(
    page_title="Data Management System",
    page_icon="📊",
    layout="centered"
)

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'entry'
if 'editing_record' not in st.session_state:
    st.session_state.editing_record = None
if 'show_delete_confirmation' not in st.session_state:
    st.session_state.show_delete_confirmation = False

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ['Data Entry', 'View Records', 'Search', 'Data Management'])
st.session_state.current_page = page.lower().replace(' ', '_')

# Add logout button in sidebar
if st.sidebar.button("Logout"):
    logout()
    st.rerun()

# Main content
st.title("Data Management System")

if st.session_state.current_page == 'data_entry':
    st.header("Data Entry")
    try:
        result = render_entry_form()
        if result:
            record_id = db.add_record(result)
            if record_id is not None:
                st.success(f"Record added successfully! ID: {record_id}")
                st.rerun()
            else:
                st.error("Failed to add record. Please try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

elif st.session_state.current_page == 'view_records':
    st.header("View Records")
    try:
        records = db.get_all_records()
        if len(records) == 0:
            st.info("No records found. Add some records using the Data Entry form.")
        else:
            for record in records:
                render_record_card(record)
    except Exception as e:
        st.error(f"Error loading records: {str(e)}")

elif st.session_state.current_page == 'search':
    st.header("Search Records")
    search_query = st.text_input("Enter name to search")

    if search_query:
        try:
            results = db.search_records(search_query)
            if len(results) == 0:
                st.info("No matching records found.")
            else:
                st.success(f"Found {len(results)} matching records")
                for record in results:
                    render_record_card(record)
        except Exception as e:
            st.error(f"Error searching records: {str(e)}")

elif st.session_state.current_page == 'data_management':
    st.header("Data Management")

    # Individual Record Deletion
    st.subheader("Delete Individual Records")
    try:
        records = db.get_all_records()
        if len(records) == 0:
            st.info("No records available to delete.")
        else:
            for record in records:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{record['full_name']}** (ID: {record['id']})")
                with col2:
                    if st.button("Delete", key=f"delete_{record['id']}"):
                        if db.delete_record(record['id']):
                            st.success(f"Record {record['id']} deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete record.")
                st.divider()
    except Exception as e:
        st.error(f"Error loading records: {str(e)}")

    # Delete All Records
    st.subheader("Delete All Records")
    st.warning("⚠️ This action cannot be undone!")

    if st.button("Delete All Records"):
        st.session_state.show_delete_confirmation = True

    if st.session_state.show_delete_confirmation:
        st.error("Are you sure you want to delete all records? This action cannot be undone!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete Everything"):
                try:
                    if db.delete_all_records():
                        st.success("All records deleted successfully!")
                        st.session_state.show_delete_confirmation = False
                        st.rerun()
                    else:
                        st.error("Failed to delete all records.")
                except Exception as e:
                    st.error(f"Error deleting all records: {str(e)}")
        with col2:
            if st.button("Cancel"):
                st.session_state.show_delete_confirmation = False
                st.rerun()

# Footer
st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    width: 100%;
    background-color: #f8f9fa;
    padding: 10px;
    text-align: center;
    color: #212529;
}
</style>
<div class="footer">
    This webapp is authority of Akhand Foundation
</div>
""", unsafe_allow_html=True)