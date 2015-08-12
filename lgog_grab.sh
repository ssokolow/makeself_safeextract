#!/bin/bash
# License: http://opensource.org/licenses/MIT
if [ "$#" -lt 1 ]; then
	echo "Usage: $0 <game-selection regexp> [additional lgogdownloader flags]"
	echo
	echo "EXPERIMENTAL wrapper script which:"
	echo " 1. Uses LGOGDownloader to download <game-selection regexp>"
	echo " 2. Uses makeself_safeextract.py to unpack the MojoSetup installers"
	echo " 3. Prunes out the MojoSetup cruft to produce a more tarball-like directory structure"
	echo " 4. Builds a new .zip file (since MojoSetup already used a Zip file with POSIX permissions)"
	echo
	echo "Again, this is EXPERIMENTAL. Not much more than a proof of concept."
	echo "It comes with absolutely no warranties, express or implied. (See MIT license)"
	exit
fi

echo "Downloading requested games..."
lgogdownloader --download --platform=4 --no-extras --no-dlc --no-language-packs --game "$@"

SELF_DIR="$(dirname "$0")"
for folder in */; do
	pushd "$folder"
	for shfile in *.sh; do
		echo "Extracting $shfile..."
		"$SELF_DIR"/makeself_safeextract.py --mojo "$shfile" || echo "Error." || exit

		echo "Pruning contents..."
		dirname="${shfile%%.sh}"
		pushd "$dirname"
		rm -rf meta scripts data/options

		tmpdirname="$(mktemp -d --tmpdir="$PWD")"
		mv data "$tmpdirname"
		if [ $(ls -1 "$tmpdirname"/data | wc -l) == "1" ]; then
			mv "$tmpdirname"/data/*/* "$tmpdirname"/*/.?* . | grep -v '/..’: '
			rmdir "$tmpdirname"/data/*
			rmdir "$tmpdirname"/data
		else
			mv "$tmpdirname"/data/* .
		fi
		rmdir "$tmpdirname"/data
		rmdir "$tmpdirname"
		popd
		
		echo "Generating $dirname.zip..."
		zip -rTm "$dirname".zip "$dirname" &&
		echo "Deleting $shfile" &&
		rm "$shfile"
	done
	popd
done