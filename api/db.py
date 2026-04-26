from __future__ import annotations

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_supabase() -> Client:
    """Return a fresh Supabase client per request.

    A singleton would share auth session state across requests — sign_in_with_password()
    overwrites the client's internal session, causing admin calls on later requests to
    run under the user JWT instead of the service role key.
    """
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)
