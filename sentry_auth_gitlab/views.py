from __future__ import absolute_import

from sentry.auth.view import AuthView

from .client import GitLabClient

from sentry.models import AuthIdentity, Team, OrganizationMember, OrganizationMemberTeam


class FetchUser(AuthView):

    def handle(self, request, helper):

        access_token = helper.fetch_state('data')['access_token']
        user = GitLabClient().get_user(access_token)
        helper.bind_state('user', user)

        return helper.next_step()


class SetTeams(AuthView):
    """View used to set sentry teams based on gitlab groups"""

    def handle(self, request, helper):

        access_token = helper.fetch_state('data')['access_token']
        user = helper.fetch_state('user')
        real_user = None

        # We fetch the User object for the current user. We need to use the
        # AuthIdentity to find it since there is no direct user access
        try:
            auth_identity = AuthIdentity.objects.select_related('user').get(
                auth_provider=helper.auth_provider,
                ident=user['id'],
            )
        except AuthIdentity.DoesNotExist:
            pass
        else:
            real_user = auth_identity.user

        if real_user:
            # We fetch the list of groups the
            groups = GitLabClient().get_groups(access_token)

            for group in groups:
                # We try to find the sentry team with the same name
                team = Team.objects.filter(name=group['name']).first()

                if team:
                    member = None

                    # We try to find the user membership for the team's
                    # organisation
                    try:
                        member = OrganizationMember.objects.get(
                            user=real_user,
                            organization=team.organization,
                        )
                    except OrganizationMember.DoesNotExist:
                        pass

                    if member:
                        # We ensure the user has access to the team (via the
                        # membership for the organisation)
                        OrganizationMemberTeam.objects.get_or_create(
                            team=team,
                            organizationmember=member,
                        )
        else:
            print("Didn't found user")

        return helper.next_step()
