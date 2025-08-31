import erbsland.conf as elcl

def parse_configuration(file_name: str):
    doc = elcl.load(file_name)
    # Access required values and check the type.
    server_name = doc.get_text("main.server.name")
    # Provide a default if the value is optional.
    port = doc.get_int("main.server.port", default=8080)
    # Iterating over section lists naturally.
    for client_value in doc["client"]:
        name = client_value.get_text("name")
        ip = client_value.get_text("ip")
        port = client_value.get_int("port", default=9000)

        # Reading values from optional sections.
        if filter_value := client_value.get("filter", default=None):
            # Requiring lists of specific types.
            keywords = filter_value.get_list("keywords", str)
            # ...
        # ...
    # ...

def main():
    try:
        parse_configuration("quick-intro.elcl")
        # ... running the application ...
        exit(0)
    except elcl.Error as e:
        print(f"Error reading the configuration.\n{e}")
        exit(1)

if __name__ == "__main__":
    main()
