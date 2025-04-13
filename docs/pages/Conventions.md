# Project Conventions

**Table of Contents**

- [Documentation](#documentation)
- [Snake Case](#snake-case)
  - [URL Names](#url-names)

## Documentation

Example:

```py
"""
This represents a model for
how documentation should be structured.

Conventions adopted from:
    - Django
    - Kafka Python
"""


def example_function():
    """
    Function summary statement.

    Parameters
    ----------
        param_1 (int): First parameter details.
        param_2 (str): Second parameter details. This one
            has a long description, so needs indentation.
    """
    pass
```

## Snake Case

The following should be in snake case to abide by Django conventions:

- Url names
  - Ex: `path(..., name="example_detail")`
- HTML file names
- Python file names

### URL Names

Additionally, url names should follow this standard:

`name="mainaction_subaction"`
