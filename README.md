# guick : a Graphical User Interface for CLI using click or Typer

## Introduction

guick (Graphical User Interface Creation Kit) can transform your command line interface
(CLI) based on click or Typer into a graphical user interface (GUI) with just a few lines of code.

guick is built on top of [click](https://click.palletsprojects.com/en/stable/) and [wxPython](https://www.wxpython.org/).


## Installation

### On Windows / MacOS

Since wxpython provides precompiled wheels for Windows and MacOS, you can simply install guick using pip:

```python

pip install guick

```

### On Linux


```python

pip install guick[all]

```

> [!NOTE]

> On Linux, no precompiled wheels are provided for wxPython on pypi and installing wxpython can be tricky.
> You can refer to the [troubleshooting section of the installation documentation](https://guick.readthedocs.io/en/latest/installation.html#troubleshooting) if you need help.

## How does it work

### If you come from click

Just add ``cls=CommandGui`` to your ``click.command``, and guick will transform your Command Line Interface into a Graphical User Interface:

Starting with the following very simple Click CLI application:

```python

import click

@click.command()
@click.option("--name")
def cli(name):
    print(f"Hello {name}!")

if __name__ == "__main__":
    cli()

```

that you would run from the command line like this:

```bash

$ python cli.py --name "John Doe"

Hello John Doe!


```

By just adding ``cls=CommandGui`` to your ``click.command``:

```python
import click
import guick

@click.command(cls=guick.CommandGui)
@click.option("--name")
def cli(name):
    print(f"Hello {name}!")

if __name__ == "__main__":
    cli()

```

You will get the following GUI:

## Support most of standard ``click`` types

- **bool** options are rendered as **CheckBox**,
- **click.Choice** options are rendered as **ComboBox**,
- **click.Path** options are rendered as **FileDialog** (with **Drag & Drop support**)
- text entries for **string** options with ``hide_input=True`` are hidden (useful for **password**)
- all other option types (including custom types) are rendred as normal text entry

> [!NOTE]
> - Multi value options (using ``nargs``) or **tuples** as option types are not yet supported.
> - Multiple options (using ``multiple=True``) are not yet supported.

## Using default values if any

Take into account **default values** for options if they are defined

## History

Keeping track of the last values of options: options fields are prefilled using the
option values from the previous run

## Separate required / optional options

The **required** and **optional** options are seperated in the GUI to clearly see what
are the mandatory options


## With validtation

Taking advantage of ``click`` validation rules, if an option doesn't pass the
validation, a red text will be shown, explaining the error.

## Standard output is redirected to the GUI

## ...with basic support of colorized Terminal log

## Automatically creates an ``Help`` menu

With hyperlink if URL is detected, enabling to go directly to the html documentation pages

## Automatically handles ``--version`` option

By adding a ``About`` section in the ``Help`` menu

## Support **group** options using notebook
