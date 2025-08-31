import erbsland.conf as elcl

def parse_configuration(file_name: str):
    doc = elcl.load(file_name)
    server_name = doc.get_text("main.server.name")
    port = doc.get_int("main.server.port", default=8080)
    clients = []
    for client_value in doc["client"]:
        name = client_value.get_text("name")
        ip = client_value.get_text("ip")
        port = client_value.get_int("port", default=9000)
        if filter_value := client_value.get("filter", default=None):
            keywords = filter_value.get_list("keywords", str)
        else:
            keywords = []
        clients.append((name, ip, port, keywords))
    print(f"Server name: {server_name}")
    print(f"Port: {port}")
    for index, client in enumerate(clients):
        print(f"Client {index}: {client}")

def main():
    try:
        parse_configuration("error_handling_4.elcl")
        print("Success!")
        exit(0)
    except elcl.Error as e:
        print(f"Error reading the configuration.")
        # print(e)
        print(e.to_text(elcl.ErrorOutput.FILENAME_ONLY | elcl.ErrorOutput.USE_LINES))
        exit(1)

if __name__ == "__main__":
    main()
