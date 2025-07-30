import os

# Other imports...

API_URL = os.environ.get('KANAPI_URL', 'http://127.0.0.1:8000/')

# Other code...

class KanList:
    def __init__(self):
        # Use API_URL here
        self.api_url = API_URL

class HorizontalScroll:
    def __init__(self):
        # Use API_URL here
        self.api_url = API_URL

# Other code...