from django import forms
from django.db.models import query

from clubs.models import Club, Team, TeamMembership
from users.models import User


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

    email = forms.CharField(max_length=100)
    club = forms.ModelChoiceField(queryset=Club.objects.all())
    send_inv = forms.BooleanField(label="Send Invite", required=True)

    