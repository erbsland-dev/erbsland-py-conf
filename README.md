
## Erbsland Configuration Parser for Python

Welcome to the implementation of the **Erbsland Configuration Language Parser**—a modern and robust configuration parser built for Python 3.12 and beyond. This implementation is designed to be secure, minimal in dependencies, and easy to integrate into your existing projects.

All you need is a Python 3.12 or newer – there are no external dependencies, no hassle.

## Project Status

- Fully implements the [Erbsland Configuration Language](https://erbsland-dev.github.io/erbsland-lang-config-doc/).
- Thoroughly tested and stable for use in productive development.
- The API is stable.
- The documentation covers the most important features.

## Quick Start

Minimal Example:
```python
import erbsland.conf as elcl
doc = elcl.load("config.elcl")
print(doc.get_int("server.port"))
```

A More Realistic Example:
```python
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
        print("Error reading the configuration.")
        print(e.to_text(elcl.ErrorOutput.FILENAME_ONLY | elcl.ErrorOutput.USE_LINES))
        exit(1)

if __name__ == "__main__":
    main()
```

## Documentation

Please read the documentation for more information about the parser and its features:

👉 [Erbsland Configuration Parser Documentation](https://config-py.erbsland.dev)

## About the Erbsland Configuration Language

The *Erbsland Configuration Language* is a human-friendly format designed for writing clear and structured configuration files. It combines a strict, well-defined syntax with flexibility in formatting, making configurations easier to read and maintain.

Here’s an example of a configuration file in a more descriptive style:

```text
# Comments are allowed almost everywhere.
---[ Main Settings ] -------------------- # A section 
App Name : "ELCL Demo"                    # Name-Value Pair with Text Value
Version  : 1                              # Name-Value Pair with Integer Value
```

And the same data in a minimal style:

```text
[main_settings] 
app_name: "ELCL Demo"
version: 1
```

Supported data types include text, integer, floating-point, boolean, date, time, datetime, time-delta, regular expressions, code, and byte sequences. These can be grouped into sections, nested via name paths, or organized into lists.

A detailed language specification is available here:

👉 [Erbsland Configuration Language Documentation](https://config-lang.erbsland.dev)

## Requirements

- Python 3.12 or newer.

## License

Copyright © 2025 Tobias Erbsland / Erbsland DEV – https://erbsland.dev/

Licensed under the **Apache License, Version 2.0**.
You may obtain a copy at: http://www.apache.org/licenses/LICENSE-2.0
Distributed on an “AS IS” basis, without warranties or conditions of any kind. See the LICENSE file for full details.

