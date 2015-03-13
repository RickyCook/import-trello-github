#!/usr/bin/env python
import argparse

parser = argparse.ArgumentParser(
    description="Import Trello cards JSON into GitHub issues"
)

def main():
    args = parser.parse_args()

if __name__ == '__main__':
    main()
