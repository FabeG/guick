# guick : a Graphical User Interface for CLI using click

## Introduction

guick (Graphical User Interface Creation Kit) can transform your command line interface
(CLI) into a graphical user interface (GUI) with just a few lines of code.

guick is built on top of [click](https://click.palletsprojects.com/en/stable/) and [wxPython](https://www.wxpython.org/).

Please note that for the moment the package can only handle **click command** (and not
**group**).

## Installation

```python

pip install guick

```

## How does it work

Just add ``cls=CommandGui`` to your ``click.command``, and guick will transform your Command Line Interface into a Graphical User Interface:

```python

   @click.command(cls=CommandGui)
   @click.option("--arg_text", help="arg_text", type=click.STRING, required=True)
   @click.option("--arg_int", help="arg_int", type=click.INT, required=True)
   @click.option("--arg_float", help="arg float", type=click.FLOAT, required=True)
   @click.option("--arg_bool", type=click.BOOL, required=True)
   @click.option("--arg_uuid", type=click.UUID, required=True)
   @click.option("--arg_filepath", type=click.Path(file_okay=True, exists=True), required=True)
   @click.option("--arg_dir", type=click.Path(dir_okay=True, exists=True), required=True)
   @click.option("--arg_choice", type=click.Choice(["choice1", "choice2"]), required=True)
   @click.option("--arg_int_range", type=click.IntRange(min=1, max=4), required=True)
   @click.option("--arg_float_range", type=click.FloatRange(min=1, max=4), required=True)
   @click.option("--arg_passwd", type=click.STRING, hide_input=True)
   def main(
       arg_text,
       arg_int,
       arg_float,
       arg_bool,
       arg_uuid,
       arg_file,
       arg_filepath,
       arg_dir,
       arg_choice,
       arg_int_range,
       arg_float_range,
       arg_passwd
    ):
       print(arg_text, arg_int, arg_float, arg_bool, arg_uuid, arg_filepath, arg_dir, arg_choice, arg_int_range, arg_float_range, arg_passwd)
   
   if __name__ == "__main__":
       main()
```

## Support most of standard ``click`` types

- **bool** options are rendered as **CheckBox**,
- **click.Choice** options are rendered as **ComboBox**,
- **click.Path** options are rendered as **FileDialog** (with **Drag & Drop support**)
- text entries for **string** options with ``hide_input=True`` are hidden (useful for **password**)
- all other option types (including custom types) are rendred as normal text entry

> [!NOTE]
> - Multi value options (using ``nargs``) or **tuples** as option types are not yet supported.
> - Multiple options (using ``multiple=True``) are not yet supported.
> - ``click.argument`` are not yet supported

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
