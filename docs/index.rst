.. guick documentation master file, created by
   sphinx-quickstart on Sat Dec 20 23:34:35 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

guick documentation
===================

.. grid:: 1 2 2 2
    :gutter: 4
    :padding: 2 2 0 0
    :class-container: sd-text-center

    .. grid-item-card:: Installation
        :class-card: intallation-card
        :shadow: md
        :link: installation
        :link-type: doc

        Installation
        +++

        .. button-ref:: Installation
            :ref-type: doc
            :click-parent:
            :color: primary
            :expand:

            Installation

    .. grid-item-card:: Quick Start Tutorial
        :class-card: quickstart-card
        :shadow: md
        :link: quickstart
        :link-type: doc

        Quick start
        +++

        .. button-ref:: quickstart
            :ref-type: doc
            :click-parent:
            :color: primary
            :expand:

            Quick Start

    .. grid-item-card:: Coming from click
        :class-card: click-card
        :shadow: md
        :link: click
        :link-type: ref

        This part of the user's guide explains how to use **guick** if you are coming from **click**.
        +++

        .. button-ref:: click
            :ref-type: ref
            :click-parent:
            :color: primary
            :expand:

            click


    .. grid-item-card:: Coming from Typer
        :class-card: typer-card
        :shadow: md
        :link: typer
        :link-type: ref

        This part of the user's guide explains how to use **guick** if you are coming from **Typer**.
        +++

        .. button-ref:: typer
            :ref-type: ref
            :click-parent:
            :color: primary
            :expand:

            Typer


.. termynal::

   $ pip install typer
   ---> 100%
   Successfully installed typer

   // Test comment 

   <span style="background-color:#009485"><font color="#D3D7CF"> FastAPI </font></span>  Starting development server 🚀
   Searching for package file structure from directories
             with <font color="#3465A4">__init__.py</font> files

   $ python main.py
   Hello World!
