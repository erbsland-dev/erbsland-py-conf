import erbsland.conf as elcl

try:
    doc = elcl.load("configuration.elcl")
    for key, value in doc.to_flat_dict().items():
        print(f"{key}: {value}")

except elcl.Error as e:
    print(f"Failed to load configuration: {e}")
