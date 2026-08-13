#!/bin/bash

SOURCE_DIR="/storage/ccmmma/prometeo/data/opendap"
DEST_DIR="/data1/ccmmma/prometeo/data/opendap"

DIRECTORIES=("aiq3" "rms3" "wcm3" "wrf5" "ww33")
SUBDIRECTORIES=("d01" "d02" "d03")

function create_links() {
	local current_dir="$1"
	local relative_path="${current_dir#$SOURCE_DIR/}"

	for item in "$current_dir"/*; do
		if [[ -f "$item" ]]; then
			local dest_file="$DEST_DIR/$relative_path/$(basename "$item")"
			if [[ ! -e "$dest_file" ]]; then
				echo $dest_file
				mkdir -p "$(dirname "$dest_file")"
				ln -s "$item" "$dest_file"
			fi
		elif [[ -d "$item" ]]; then
			create_links "$item"
		fi
	done
}

for dir in "${DIRECTORIES[@]}"; do
	for subdir in "${SUBDIRECTORIES[@]}"; do
		source_path="$SOURCE_DIR/$dir/$subdir/archive"
		if [[ -d "$source_path" ]]; then
			create_links "$source_path"
		fi
	done
done
