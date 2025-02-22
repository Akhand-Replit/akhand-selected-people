import pandas as pd
from datetime import datetime
import base64

class Storage:
    def __init__(self):
        self.data = pd.DataFrame(columns=[
            'id', 'full_name', 'father_name', 'mother_name', 
            'dob', 'gender', 'nid', 'voter_no', 
            'permanent_address', 'present_address',
            'image_data', 'pdf_urls', 'mobile_numbers',
            'whatsapp_numbers', 'facebook_links', 'website_links',
            'description', 'created_at'
        ])

    def add_record(self, record):
        record['id'] = len(self.data)
        record['created_at'] = datetime.now()
        self.data = pd.concat([self.data, pd.DataFrame([record])], ignore_index=True)
        return record['id']

    def get_all_records(self):
        return self.data.sort_values('created_at', ascending=False)

    def get_record(self, record_id):
        return self.data[self.data['id'] == record_id].iloc[0] if len(self.data[self.data['id'] == record_id]) > 0 else None

    def update_record(self, record_id, updated_data):
        if 'id' in updated_data:
            del updated_data['id']
        if 'created_at' in updated_data:
            del updated_data['created_at']

        # Handle list and dict fields properly
        for key, value in updated_data.items():
            self.data.loc[self.data['id'] == record_id, key] = value
        return True

    def search_records(self, query):
        return self.data[self.data['full_name'].str.contains(query, case=False, na=False)]

# Global storage instance
storage = Storage()