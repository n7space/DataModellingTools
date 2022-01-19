#!/usr/bin/env python3

import sys

from sqlalchemy import MetaData
from sqlalchemy_schemadisplay import create_schema_graph

def create_diagram(path: str, name: str):
    # create the pydot graph object by autoloading all tables via a bound metadata object
    # path is the link to the database such as postgresql+psycopg2://taste:tastedb@localhost/blah
    graph = create_schema_graph(
        metadata=MetaData(path),
        show_datatypes=False,  # The image would get too big if we'd show the datatypes
        show_indexes=False,    # ditto for indexes
        rankdir='LR',          # From left to right (instead of top to bottom)
        concentrate=True       # Don't try to join the relation lines together
    )
    graph.write_png(f'{name}.png')  # write out the file
    

def main():
    if len(sys.argv) < 3:
        print("Usage: " + sys.argv[0] + ' <path to database> <database_name>')
        print(f"e.g. {sys.argv[0]} postgresql+psycopg2://taste:tastedb@localhost/blah blah")
        sys.exit(1)
    create_diagram(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
