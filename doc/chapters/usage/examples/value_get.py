import erbsland.conf as elcl

try:
    doc = elcl.load("configuration.elcl")

    server_port = doc.get_int("server.port")
    server_host = doc.get_text("server.host")

    port = doc.get_int("server.port", default=8080)
    host = doc.get_text("server.host", default="localhost")

    keywords = doc.get_list("filter.keywords", str)

    text = doc["main.value"].convert_to(str)

except elcl.Error as e:
    print(f"Failed to load configuration: {e}")
