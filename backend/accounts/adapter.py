from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """
    Sign-up only asks for email + password. New users start with
    username == email, which the frontend treats as "profile setup needed"
    (see UserProfileView.need_setup) and prompts for a real username.
    """

    def populate_username(self, request, user):
        user.username = user.email.lower().strip()
