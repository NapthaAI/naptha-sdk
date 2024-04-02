from dotenv import load_dotenv
import jwt
import os
from payments_py import Payments, Environment
from surrealdb import Surreal
from typing import Dict, List, Tuple, Optional

load_dotenv()

class Hub:
    """The Hub class is the entry point into Naptha Hub."""

    def __init__(self, *args, **kwargs):
        self.payments = Payments(session_key=os.getenv("SESSION_KEY"), environment=Environment.appTesting, version="0.1.0", marketplace_auth_token=os.getenv("MARKETPLACE_AUTH_TOKEN"))
        self.naptha_plan_did = os.getenv("NAPTHA_PLAN_DID")
        self.wallet_address = "0x0106B8532816e6DAdC377697CC58072eD6023075"

    def show_credits(self):
        response = self.payments.get_subscription_balance(self.naptha_plan_did, self.wallet_address)
        print('=========', response.content)

    def get_service_details(self, service_did):
        response = self.payments.get_service_details(service_did)
        print('=========', response)
