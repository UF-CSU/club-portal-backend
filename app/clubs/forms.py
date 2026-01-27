from django import forms
from users.models import User

from clubs.models import Club, Team, TeamMembership


class TeamMembershipForm(forms.ModelForm):
    """Manage team memberships."""

    user = forms.ModelChoiceField(queryset=User.objects.all())
    team = forms.ModelChoiceField(queryset=Team.objects.all())

    class Meta:
        model = TeamMembership
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not hasattr(self, "parent_model"):
            self.fields["user"].queryset = User.objects.none()

            return

        self.fields["team"].initial = self.parent_model
        self.fields["user"].queryset = User.objects.filter(
            club_memberships__club__id=self.parent_model.club.id
        )


class AdminInviteForm(forms.Form):
    """Invite Club Admin"""

    email = forms.EmailField(
        max_length=100,
        help_text="Get or create user with this email",
        required=True,
    )
    club = forms.ModelChoiceField(
        queryset=Club.objects.all(), help_text="Assign user to this club", required=True
    )
    is_owner = forms.BooleanField(
        label="Is Owner",
        required=False,
        initial=True,
        help_text="Make this user the owner of the club",
    )
    send_invite = forms.BooleanField(
        label="Send Invite",
        required=False,
        initial=False,
        help_text="If true, will send club invitation email (separate from account setup email)",
    )
