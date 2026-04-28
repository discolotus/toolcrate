# ToolCrate Examples

This directory contains example files for various ToolCrate features.

## Batch URL Processing

The `urls.txt` file demonstrates the format for batch URL processing with the `--links-file` option:

```bash
# Process all links in the file
toolcrate sldl --links-file urls.txt

# Process links with custom download path
toolcrate sldl --links-file urls.txt --download-path ~/Music/my-downloads
```

### File Format

The URLs file should contain one link per line. Lines starting with `#` are treated as comments and ignored.

Example file content (see `urls.txt`):

```
# Sample URLs for toolcrate sldl batch processing
# This file contains links to be processed one by one
# Each link will be processed as a separate download
# Comments (lines starting with #) are ignored

https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://soundcloud.com/octobersveryown/drake-gods-plan
```

### Benefits

- Process large numbers of links without manual intervention
- Keep organized lists of music to download
- Automatically apply the same download options to all links 