import erbsland.conf as elcl
from erbsland.conf import ConfTypeMismatch

try:
    doc = elcl.load("configuration.elcl")

    server_port = doc["server.port"].as_int()
    server_host = doc["server.host"].as_text()

    value_x = doc["main.x"]
    if x := value_x.as_int(default=None):
        print(f"x is int: {x}")
    elif x := value_x.as_text(default=None):
        print(f"x is text: {x}")
    else:
        raise ConfTypeMismatch(
            "Expected integer or text value",
            source=value_x.location,
            name_path=value_x.name_path
        )

    int_list = doc["main.ports"].as_list(int)
    str_list = doc["main.names"].as_list(str)

    tag_value = doc["main.tag"]
    if tag_value.type in [elcl.ValueType.TEXT, elcl.ValueType.INTEGER]:
        tag = tag_value.native()
        tag2 = doc["main.tag2"].as_type(type(tag))
        tag3 = doc["main.tag3"].as_type(type(tag))

except elcl.Error as e:
    print(f"Failed to load configuration: {e}")
