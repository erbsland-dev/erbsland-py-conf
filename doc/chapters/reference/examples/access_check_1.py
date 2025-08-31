from erbsland.conf import AccessFeature, FileAccessCheck, Parser

flags = (
        AccessFeature.SAME_DIRECTORY |
        AccessFeature.SUBDIRECTORIES |
        AccessFeature.LIMIT_SIZE |
        AccessFeature.REQUIRE_SUFFIX
)
access_check = FileAccessCheck(flags)
parser = Parser()
parser.access_check = access_check
parser.parse("configuration.elcl")
