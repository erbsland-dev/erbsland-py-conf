from erbsland.conf import AccessCheck, AccessCheckResult, AccessSources

class MyAccessCheck(AccessCheck):
    def check(self, access_sources: AccessSources) -> AccessCheckResult:
        # ...
        return AccessCheckResult.GRANTED
