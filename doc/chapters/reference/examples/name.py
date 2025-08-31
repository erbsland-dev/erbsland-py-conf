import erbsland.conf as elcl

doc = elcl.load("configuration.elcl")

# Implicit parsed name-path
port = doc.get_int("main.server.port")

# Pre-parsed name-path
NP_PORT = elcl.NamePath.from_text("main.server.port")
for server in doc["main.server"]:
    port = server.get_int(NP_PORT)

path1 = elcl.NamePath.from_text("main.server")
path2 = elcl.NamePath.from_text("filter.keywords")

# Path operations
path3 = path1 / path2
path1.append(path2)

# Assemble a path from Name instances.
assembled_path = elcl.NamePath([
    elcl.Name.create_regular("translations"),
    elcl.Name.create_text("Welcome!"),
])
