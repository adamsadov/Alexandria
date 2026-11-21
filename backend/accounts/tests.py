import re
from urllib.parse import unquote

from django.core import mail
from django.test import Client, TestCase, override_settings

from library.models import Shelf, User

AUTH = "/_allauth/browser/v1/auth"


@override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory", ACCOUNT_RATE_LIMITS=False)
class AllauthSessionFlowTests(TestCase):
    """
    End-to-end checks of the allauth headless flow the frontend uses:
    sign up -> verify email -> session cookie -> protected API -> logout -> login.
    CSRF is enforced, as it is in the browser.
    """

    email = "reader@example.com"
    password = "a-Long-test-passw0rd"

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    # helpers
    def csrf(self):
        self.client.get("/api/auth/csrf/")
        return self.client.cookies["csrftoken"].value

    def post(self, url, data):
        return self.client.post(
            url, data, content_type="application/json", HTTP_X_CSRFTOKEN=self.csrf()
        )

    def sign_up_and_verify(self):
        resp = self.post(f"{AUTH}/signup", {"email": self.email, "password": self.password})
        # Mandatory verification: allauth reports a pending verify_email flow.
        self.assertEqual(resp.status_code, 401)
        flows = {f["id"]: f for f in resp.json()["data"]["flows"]}
        self.assertTrue(flows["verify_email"].get("is_pending"))

        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"http://localhost:3000/auth/verify-email/(\S+)", mail.outbox[0].body)
        self.assertIsNotNone(link, mail.outbox[0].body)

        resp = self.post(f"{AUTH}/email/verify", {"key": unquote(link.group(1))})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["meta"]["is_authenticated"])

    # tests
    def test_csrf_endpoint_sets_cookie(self):
        resp = self.client.get("/api/auth/csrf/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("csrftoken", resp.cookies)

    def test_signup_creates_user_profile_and_default_shelves(self):
        self.sign_up_and_verify()
        user = User.objects.get(email=self.email)
        self.assertEqual(user.username, self.email)  # triggers profile setup
        self.assertTrue(hasattr(user, "related_user_profile"))
        self.assertEqual(Shelf.objects.filter(user=user).count(), 5)

    def test_session_grants_access_to_protected_api(self):
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, 401)
        self.sign_up_and_verify()
        resp = self.client.get("/api/auth/profile/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["need_setup"])

    def test_writes_require_csrf_token(self):
        self.sign_up_and_verify()
        url = "/api/auth/user/profile/update/"
        no_token = self.client.post(url, {"bio": "hi"}, content_type="application/json")
        self.assertEqual(no_token.status_code, 403)
        with_token = self.post(url, {"bio": "hi"})
        self.assertEqual(with_token.status_code, 200)
        self.assertEqual(User.objects.get(email=self.email).related_user_profile.bio, "hi")

    def test_logout_then_login(self):
        self.sign_up_and_verify()
        resp = self.client.delete(f"{AUTH}/session", HTTP_X_CSRFTOKEN=self.csrf())
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, 401)

        bad = self.post(f"{AUTH}/login", {"email": self.email, "password": "wrong-password"})
        self.assertEqual(bad.status_code, 400)

        resp = self.post(f"{AUTH}/login", {"email": self.email, "password": self.password})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, 200)

    def test_unverified_user_cannot_log_in(self):
        self.post(f"{AUTH}/signup", {"email": self.email, "password": self.password})
        self.client.delete(f"{AUTH}/session", HTTP_X_CSRFTOKEN=self.csrf())
        resp = self.post(f"{AUTH}/login", {"email": self.email, "password": self.password})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, 401)

    def test_password_reset_sends_frontend_link(self):
        self.sign_up_and_verify()
        mail.outbox.clear()
        resp = self.post(f"{AUTH}/password/request", {"email": self.email})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"http://localhost:3000/auth/reset-password/(\S+)", mail.outbox[0].body)
        self.assertIsNotNone(link, mail.outbox[0].body)

        new_password = "another-Long-passw0rd"
        resp = self.post(f"{AUTH}/password/reset", {"key": unquote(link.group(1)), "password": new_password})
        # Reset succeeds and ends the session; the user then logs in again.
        self.assertEqual(resp.status_code, 401, resp.content)
        self.assertTrue(User.objects.get(email=self.email).check_password(new_password))

    def test_session_endpoint_reports_user(self):
        self.assertEqual(self.client.get(f"{AUTH}/session").status_code, 401)
        self.sign_up_and_verify()
        resp = self.client.get(f"{AUTH}/session")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["user"]["email"], self.email)
