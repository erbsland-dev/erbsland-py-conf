import erbsland.conf as elcl

try:
    doc = elcl.load("configuration.elcl")

    print(doc.to_test_value_tree(
        elcl.TestOutput.MINIMAL_ESC |
        elcl.TestOutput.POSITION |
        elcl.TestOutput.SOURCE_ID |
        elcl.TestOutput.ALIGN_VALUES))

except elcl.Error as e:
    print(f"Failed to load configuration: {e}")
