# Grabs the current directory and the path to this file for use in other scripts
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir := $(dir $(mkfile_path))
project_dir := $(mkfile_dir)
src_dir := $(project_dir)src/

### Build ###

build:
	$(src_dir)make_mod.sh
.PHONY: build

run: build
.PHONY: run

### Clean ###

clean:
	rm -rf $(project_dir)build/
	rm -rf $(src_dir)__pycache__/
.PHONY: clean

reset: clean
.PHONY: reset
