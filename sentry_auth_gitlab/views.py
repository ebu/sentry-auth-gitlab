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
    def handle(self, request, helper):
        access_token = helper.fetch_state('data')['access_token']
        user = helper.fetch_state('user')

        real_user = None

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

            groups = GitLabClient().get_groups(access_token)

            for group in groups:

                team = Team.objects.filter(name=group['name']).first()

                if team:

                    member = None

                    try:
                        member = OrganizationMember.objects.get(
                            user=real_user,
                            organization=team.organization,
                        )
                    except OrganizationMember.DoesNotExist:
                        continue

                    if member:

                        OrganizationMemberTeam.objects.get_or_create(
                            team=team,
                            organizationmember=member,
                        )
        else:
            print("Didn't found user")

        return helper.next_step()
