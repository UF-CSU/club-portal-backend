from django import forms

from clubs.models import Team, TeamMembership
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
