import streamlit as st
from datetime import datetime
from utils import load_image, display_image, process_pdf
from typing import List, Dict, Any, Optional
from database import db

def render_multiple_inputs(label: str, key_prefix: str, initial_values: Optional[List[str]] = None) -> List[str]:
    """Render multiple input fields dynamically"""
    values = []
    inputs = st.session_state.get(f"{key_prefix}_count", max(1, len(initial_values or [])))

    for i in range(inputs):
        value = st.text_input(
            f"{label} #{i+1}", 
            value=initial_values[i] if initial_values and i < len(initial_values) else "",
            key=f"{key_prefix}_{i}"
        )
        if value:
            values.append(value)

    # Add field button
    if st.session_state.get('add_' + key_prefix):
        st.session_state[f"{key_prefix}_count"] = inputs + 1
        st.session_state['add_' + key_prefix] = False
        st.rerun()

    return values

def render_entry_form(record: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Render the data entry form, optionally pre-filled with record data"""
    # Initialize session state for dynamic fields
    for key_prefix in ['mobile', 'whatsapp', 'facebook', 'website']:
        if f"{key_prefix}_count" not in st.session_state:
            st.session_state[f"{key_prefix}_count"] = 1

    st.subheader("Personal Information")

    with st.form("entry_form", clear_on_submit=not bool(record)):
        # Basic Information
        full_name = st.text_input("Full Name*", value=record.get('full_name', '') if record else '')
        father_name = st.text_input("Father's Name*", value=record.get('father_name', '') if record else '')
        mother_name = st.text_input("Mother's Name*", value=record.get('mother_name', '') if record else '')

        # Handle date input
        try:
            default_date = datetime.strptime(record['dob'], '%Y-%m-%d').date() if record and record.get('dob') else datetime.now().date()
        except (TypeError, ValueError):
            default_date = datetime.now().date()

        dob = st.date_input("Date of Birth*", value=default_date)

        gender_options = ["Male", "Female", "Other"]
        current_gender = record.get('gender') if record else None
        gender_index = gender_options.index(current_gender) if current_gender in gender_options else 0
        gender = st.selectbox("Gender*", gender_options, index=gender_index)

        # ID Information
        col1, col2 = st.columns(2)
        with col1:
            nid = st.text_input("National ID (NID) Number*", value=record.get('nid', '') if record else '')
        with col2:
            voter_no = st.text_input("Voter Number", value=record.get('voter_no', '') if record else '')

        # Addresses
        permanent_address = st.text_area("Permanent Address*", value=record.get('permanent_address', '') if record else '')
        present_address = st.text_area("Present Address*", value=record.get('present_address', '') if record else '')

        # File Uploads and Links
        st.subheader("Documents")
        image_file = st.file_uploader("Upload Profile Image", type=['png', 'jpg', 'jpeg'])
        pdf_links = render_multiple_inputs("PDF Document Links (Gdrive or other)", "pdf_links", 
            record.get('pdf_urls', []) if record else None)

        # Contact Information
        st.subheader("Contact Information")
        mobile_numbers = render_multiple_inputs("Mobile Number", "mobile", 
            record.get('mobile_numbers', []) if record else None)
        whatsapp_numbers = render_multiple_inputs("WhatsApp Number", "whatsapp", 
            record.get('whatsapp_numbers', []) if record else None)
        facebook_links = render_multiple_inputs("Facebook Profile", "facebook", 
            record.get('facebook_links', []) if record else None)
        website_links = render_multiple_inputs("Website", "website", 
            record.get('website_links', []) if record else None)

        # Description
        st.subheader("Additional Information")
        description = st.text_area("Description", value=record.get('description', '') if record else '')

        submitted = st.form_submit_button("Save Changes" if record else "Submit")

        if submitted:
            if not all([full_name, father_name, mother_name, nid, permanent_address, present_address]):
                st.error("Please fill all required fields marked with *")
                return None

            # Process image and PDF files
            image_data = None
            if image_file:
                image_data = load_image(image_file)
            elif record and record.get('image_data'):
                image_data = record['image_data']

            # Use PDF links directly
            pdf_urls = pdf_links

            return {
                'id': record['id'] if record else None,
                'full_name': full_name,
                'father_name': father_name,
                'mother_name': mother_name,
                'dob': dob.strftime('%Y-%m-%d'),
                'gender': gender,
                'nid': nid,
                'voter_no': voter_no,
                'permanent_address': permanent_address,
                'present_address': present_address,
                'image_data': image_data,
                'pdf_urls': pdf_urls,
                'mobile_numbers': mobile_numbers,
                'whatsapp_numbers': whatsapp_numbers,
                'facebook_links': facebook_links,
                'website_links': website_links,
                'description': description
            }

    # Add buttons outside the form for adding new fields
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("+ Add Mobile Number"):
            st.session_state['add_mobile'] = True
    with col2:
        if st.button("+ Add WhatsApp"):
            st.session_state['add_whatsapp'] = True
    with col3:
        if st.button("+ Add Facebook"):
            st.session_state['add_facebook'] = True
    with col4:
        if st.button("+ Add Website"):
            st.session_state['add_website'] = True

    return None

def render_record_card(record: Dict[str, Any]):
    """Render a single record card"""
    with st.container():
        st.markdown("""
        <style>
        .record-card {
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #ddd;
            margin-bottom: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                if record.get('image_data'):
                    if isinstance(record['image_data'], dict):
                        st.image(record['image_data']['url'])
                    else:
                        st.markdown(display_image(record['image_data']), unsafe_allow_html=True)

            with col2:
                st.markdown(f"### {record['full_name']}")
                st.markdown(f"**NID:** {record['nid']}")
                if record.get('voter_no'):
                    st.markdown(f"**Voter No:** {record['voter_no']}")
                st.markdown(f"**Gender:** {record['gender']}")

            with col3:
                if st.button("Edit Record", key=f"edit_{record['id']}"):
                    st.session_state['editing_record'] = record['id']
                    st.rerun()

            # Show edit form if this record is being edited
            if st.session_state.get('editing_record') == record['id']:
                st.markdown("### Edit Record")
                updated_data = render_entry_form(record)
                if updated_data:
                    if db.update_record(record['id'], updated_data):
                        st.success("Record updated successfully!")
                        st.session_state['editing_record'] = None
                        st.rerun()
                    else:
                        st.error("Failed to update record. Please try again.")
            else:
                with st.expander("View Details"):
                    st.markdown(f"**Father's Name:** {record['father_name']}")
                    st.markdown(f"**Mother's Name:** {record['mother_name']}")
                    st.markdown(f"**Date of Birth:** {record['dob']}")
                    st.markdown(f"**Permanent Address:** {record['permanent_address']}")
                    st.markdown(f"**Present Address:** {record['present_address']}")

                    if record.get('pdf_urls'):
                        st.markdown("**PDF Documents:**")
                        for url in record['pdf_urls']:
                            st.markdown(f"- [View Document]({url})")

                    if record.get('mobile_numbers'):
                        st.markdown("**Mobile Numbers:**")
                        for num in record['mobile_numbers']:
                            st.markdown(f"- {num}")

                    if record.get('whatsapp_numbers'):
                        st.markdown("**WhatsApp Numbers:**")
                        for num in record['whatsapp_numbers']:
                            st.markdown(f"- {num}")

                    if record.get('facebook_links'):
                        st.markdown("**Facebook Profiles:**")
                        for link in record['facebook_links']:
                            st.markdown(f"- [{link}]({link})")

                    if record.get('website_links'):
                        st.markdown("**Websites:**")
                        for link in record['website_links']:
                            st.markdown(f"- [{link}]({link})")

                    if record.get('description'):
                        st.markdown("**Description:**")
                        st.markdown(record['description'])