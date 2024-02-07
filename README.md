[![Build and Test Status of Data Modelling Tools on Gitlab CI](https://gitrepos.estec.esa.int/taste/dmt/badges/master/pipeline.svg)](https://gitrepos.estec.esa.int/taste/dmt/-/commits/master)

TASTE Data Modelling Tools
==========================

These are the tools used by the European Space Agency's [TASTE toolchain](https://taste.tools/)
to automate handling of the Data Modelling. They include more than two
dozen codegenerators that automatically create the 'glue'; that is, the run-time translation
bridges that allow code generated by modelling tools (Simulink, OpenGeode, etc)
to "speak" to one another, via ASN.1 marshalling.

For the encoders and decoders of the messages
themselves, TASTE uses [ASN1SCC](https://github.com/maxime-esa/asn1scc) - an ASN.1
compiler specifically engineered for safety-critical environments.

For more details, visit the [TASTE site](https://taste.tools/).

Installation
------------

For using the tools, this should suffice:

    $ sudo apt-get install libxslt1-dev libxml2-dev zlib1g-dev python3-pip
    $ ./configure
    $ # Optionally, configure a Python virtual environment (via venv)
    $ # to avoid "polluting" your system-level Python with dependencies
    $ # you may not want.
    # # But whether with an activated venv or not, you end with:
    $ pip3 install --user --upgrade .

For developing the tools, the packaged Makefile allow for easy static-analysis
via the dominant Python static analyzers and syntax checkers:

    $ make flake8  # check for pep8 compliance
    $ make pylint  # static analysis with pylint
    $ make mypy    # type analysis with mypy

Contents
--------

What is packaged:

- **commonPy** (*library*)

    Contains the basic API for parsing ASN.1 (via invocation of 
    [ASN1SCC](https://github.com/maxime-esa/asn1scc) and simplification
    of the generated XML AST representation to the Python classes
    inside `asnAST.py`. The class diagram with the AST classes
    is [packaged in the code](dmt/commonPy/asnAST.py#L42).

- **asn2aadlPlus** (*utility*)

    Converts the type declarations inside ASN.1 grammars to AADL
    declarations, that are used by [TASTE](https://taste.tools)
    to generate the executable containers.

- **asn2dataModel** (*utility*)

    Reads the ASN.1 specification of the exchanged messages, and generates
    the semantically equivalent Modeling tool/Modeling language declarations
    (e.g. Matlab/Simulink, etc). 

    The actual mapping logic exists in plugins, called *A mappers*
    (`simulink_A_mapper.py` handles Simulink/RTW,
    handles SCADE6, `ada_A_mapper.py` generates Ada types,
    `sqlalchemy_A_mapper.py`, generates SQL definitions via SQLAlchemy, etc)

- **aadl2glueC** (*utility*)

    Reads the AADL specification of the system, and then generates the runtime
    bridge-code that will map the message data structures from those generated
    by [ASN1SCC](https://github.com/maxime-esa/asn1scc) to/from those generated
    by the modeling tool (that is used to functionally model the subsystem;
    e.g. Matlab/Simulink, C, Ada, etc).

Contact
-------

For bug reports, please use the Issue Tracker; for any other communication,
contact ESA:

    Maxime.Perrotin@esa.int
    System, Software and Technology Department
    European Space Agency

    ESTEC / TEC-SWT
    Keplerlaan 1, PO Box 299
    NL-2200 AG Noordwijk, The Netherlands
