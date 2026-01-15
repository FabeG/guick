# guick : a Graphical User Interface for CLI using Click or Typer

## Introduction

guick (Graphical User Interface Creation Kit) can transform your command line interface
(CLI) based on [Click](https://click.palletsprojects.com/en/stable/) or [Typer](https://typer.tiangolo.com/) into a graphical user interface (GUI) with just a few lines of code.

guick is built on top of [Click](https://click.palletsprojects.com/en/stable/) and [wxPython](https://www.wxpython.org/).


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
> On Linux, no precompiled wheels are provided for wxpython on pypi and installing wxpython can be tricky.
> You can refer to the [troubleshooting section of the installation documentation](https://guick.readthedocs.io/en/latest/installation.html#troubleshooting) if you need help.

## A simple example

### If you come from ``Click``

Just add ``cls=CommandGui`` to your ``click.command``, and guick will transform your Command Line Interface into a Graphical User Interface:

Starting with the following very simple Click CLI application (file ``click_first_basic_example.py``):

```python
import click


@click.command()
@click.option("--name")
def first_basic_example(name):
    print(f"Hello {name}!")


if __name__ == "__main__":
    first_basic_example()
```

that you would run from the command line like this:

```console
$ python click_first_basic_example.py --name "John Doe"

Hello John Doe!
```

By just adding ``cls=CommandGui`` to your ``click.command``:

```diff
import click
+import guick


+@click.command(cls=guick.CommandGui)
@click.option("--name")
def first_basic_example(name):
    print(f"Hello {name}!")


if __name__ == "__main__":
    first_basic_example()
```

and run the application **with no arguments**:

```console
$ python click_first_basic_example.py
```

You will get the following GUI:

![First Click example](/docs/images/click_basic_first_example.gif)


### If you come from ``Typer``

Starting with the following very simple ``Typer`` CLI application (file
``typer_first_basic_example.py``):

```python
import typer

app = typer.Typer()


@app.command()
def first_basic_example(name: str):
    print(f"Hello {name}!")


if __name__ == "__main__":
    app()
```

that you would run from the command line like this:

```console
$ python typer_first_basic_example.py --name "John Doe"

Hello John Doe!

```

By just adding ``cls=TyperCommand`` to your ``app.command``:

```diff
+import guick
import typer

app = typer.Typer()


+@app.command(cls=guick.TyperCommandGui)
def first_basic_example(name: str):
    print(f"Hello {name}!")


if __name__ == "__main__":
    app()
```

and run the application **with no arguments**:

```console

$ python typer_first_basic_example.py

```

You will get the following GUI:

![First Typer example](/docs/images/typer_basic_first_example.gif)

## An example with subcommands

In the following example (taken from the excellent [Typer documentation](https://typer.tiangolo.com/#example-upgrade)), we will consider a Typer app with 2 subcommands.

In order to generate the GUI, we only have to add 2 lines of code:


```diff
+import guick
import typer

+app = typer.Typer(cls=guick.TyperGroupGui)


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")


if __name__ == "__main__":
    app()
```

And by running the application with **no arguments**:

```console
$ python typer_subcommands_example.py
```

The following GUI will be displayed:

![Typer subcommand example](/docs/images/typer_subcommands_example.gif)

## Support most of standard ``Click`` / ``Typer`` types

- **bool** options are rendered as **CheckBox**,
- **click.Choice** / Enum options are rendered as **ComboBox**,
- **click.Path** / **click.File** options are rendered as **FileDialog** (with **Drag & Drop support**)
- **click.types.IntRange** options are rendered as **Slider**
- **click.DateTime** options are rendered using a **DateTimePicker**
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
