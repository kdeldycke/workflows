#!/usr/bin/env bash
# Helper script to prepare the project for tagging.

# Extract current version.
RELEASE_VERSION=`grep "current_version = " ./.bumpversion.cfg | cut -d ' ' -f 3`
echo $RELEASE_VERSION

# Hard-code the version number in callable workflows.
find ./.github/workflows -type f -name "*.yaml" -print | xargs perl -pi -e s,main\/requirements.txt,v${RELEASE_VERSION}\/requirements.txt,g

# Set the released date to today in the changelog.
perl -pi -e "s/\(unreleased\)/\(`date +'%Y-%m-%d'`\)/" ./changelog.md

# Update the comparison URL.
perl -pi -e "s/\.\.\.main\)/\.\.\.v${RELEASE_VERSION}\)/" ./changelog.md

# Remove the warning message.
perl -i -ne "print if not /\`\`\`/ .. /^$/" ./changelog.md
