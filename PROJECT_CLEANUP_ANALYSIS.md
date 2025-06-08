# ToolCrate Project Cleanup Analysis

## Current Project Structure Overview

The ToolCrate project is a Python package that integrates multiple music management tools (Shazam recognition, Soulseek downloading, etc.) into a unified CLI interface. The project currently has several organizational issues that need addressing before becoming a proper git repository.

## Key Findings

### 1. Duplicate Repository Clones
**Issue**: The project contains duplicate clones of external repositories:
- `fresh-slsk-batchdl/` (root level) - Contains a complete git repo clone
- `src/slsk-batchdl/` - Another clone of the same repo (different fork URL)
- `src/Shazam-Tool/` - Clone of Shazam tool repository

**Problem**: Having full repository clones with `.git` directories creates unnecessary bloat and conflicts with the main project's git structure.

### 2. Inconsistent Packaging Configuration
**Issue**: The project has both `setup.py` and `pyproject.toml` with conflicting configurations:
- `setup.py`: Uses setuptools, version 0.1.0, targets Python 3.11-3.12
- `pyproject.toml`: Uses Poetry, version 0.1.0, targets Python >=3.8
- Different dependency specifications and entry points

### 3. Configuration File Duplication
**Issue**: Multiple config files with overlapping purposes:
- `toolcrate.conf` (main config)
- `sldl.conf` (root level, contains credentials!)
- `config/sldl.conf` (another sldl config)

**Security Risk**: `sldl.conf` contains hardcoded credentials that shouldn't be in version control.

### 4. Scattered Log and Temporary Files
**Issue**: Multiple directories contain runtime files:
- `logs/` - Application logs
- `config/cron.log` (4.5MB!)
- `config/wishlist.log` (276KB)
- `tmp/` directory
- `.DS_Store` files throughout

### 5. Ad-hoc Scripts at Root Level
**Issue**: Several one-off scripts in root directory:
- `download_s7_tracks.sh` - Specific playlist download script
- `test_command.sh` / `test_command_revised.sh` - Test scripts
- `playlists.txt` - Hardcoded playlist data

### 6. Complex Installation Process
**Issue**: The `install.sh` script (222 lines) does too many things:
- Python version checking
- Virtual environment setup
- Git submodule handling
- External tool compilation
- Global PATH modification
- Multiple installation methods

## Recommendations

### Phase 1: Immediate Cleanup

#### A. Remove Duplicate Repository Clones
1. **DELETE**: `fresh-slsk-batchdl/` (entire directory)
2. **KEEP**: `src/slsk-batchdl/` and `src/Shazam-Tool/` as git submodules
3. **UPDATE**: `.gitmodules` to reference your own forks

#### B. Consolidate Configuration Files
1. **KEEP**: `toolcrate.conf` as main config template
2. **DELETE**: `sldl.conf` (move credentials to user-specific config)
3. **MOVE**: `config/sldl.conf` to `examples/sldl.conf.example`
4. **ADD**: `sldl.conf` to `.gitignore`

#### C. Clean Up Root Directory
1. **DELETE**: 
   - `download_s7_tracks.sh` (move to `examples/` if needed)
   - `test_command*.sh` 
   - `playlists.txt` (move to `examples/`)
   - All `.DS_Store` files
2. **MOVE**:
   - `run_tests.sh` → `scripts/run_tests.sh`

#### D. Handle Runtime/Generated Files
1. **ADD to .gitignore**:
   - `logs/`
   - `tmp/`
   - `config/*.log`
   - `.DS_Store`
   - `__pycache__/`
   - `.pytest_cache/`
   - `.venv/`
   - `pip-wheel-metadata/`
2. **DELETE** existing log files and temp data

### Phase 2: Repository Structure Reorganization

#### Recommended New Structure:
```
toolcrate/
├── README.md
├── LICENSE
├── pyproject.toml                    # Single packaging config
├── .gitmodules                       # Updated with your forks
├── .gitignore                        # Comprehensive ignore rules
├── docker-compose.yml               # Keep if still needed
├── src/
│   ├── toolcrate/                   # Main package
│   ├── slsk-batchdl/               # Submodule → your fork
│   └── Shazam-Tool/                # Submodule → your fork
├── tests/
├── examples/
│   ├── README.md
│   ├── urls.txt
│   ├── sldl.conf.example
│   ├── toolcrate.conf.example
│   └── download_playlist_example.sh
├── scripts/
│   ├── install.sh                  # Simplified installer
│   └── run_tests.sh
└── docs/                           # Future documentation
```

#### E. Simplify Package Configuration
1. **DELETE**: `setup.py` (keep only `pyproject.toml`)
2. **UPDATE**: `pyproject.toml` with correct Python version constraints
3. **STANDARDIZE**: Entry points and dependencies

### Phase 3: Fork Management Strategy

#### Create Your Own Forks
1. **Fork** `fiso64/slsk-batchdl` to your GitHub account
2. **Fork** `in0vik/Shazam-Tool` to your GitHub account  
3. **UPDATE** `.gitmodules` to point to your forks:
   ```
   [submodule "src/slsk-batchdl"]
       path = src/slsk-batchdl
       url = https://github.com/YOURUSERNAME/slsk-batchdl.git
   [submodule "src/Shazam-Tool"]
       path = src/Shazam-Tool
       url = https://github.com/YOURUSERNAME/Shazam-Tool.git
   ```

#### Simplify Installation Process
1. **REWRITE** `install.sh` to be much simpler:
   - Check Python version
   - Create venv
   - Install package with pip
   - Initialize submodules
   - Basic setup only

2. **MOVE** complex setup logic into:
   - `pyproject.toml` build scripts
   - Package installation hooks
   - User configuration prompts in CLI

### Phase 4: Configuration Management

#### User-Specific Configuration
1. **CREATE** `~/.config/toolcrate/` directory structure
2. **MOVE** credentials and user-specific settings out of repo
3. **PROVIDE** example configs in `examples/`
4. **IMPLEMENT** first-run configuration wizard

## Files to Delete Immediately

```
fresh-slsk-batchdl/                  # Duplicate repository
download_s7_tracks.sh                # Ad-hoc script
test_command.sh                      # Test remnant
test_command_revised.sh              # Test remnant  
playlists.txt                        # Hardcoded data
sldl.conf                           # Contains credentials!
config/cron.log                      # Large log file
config/wishlist.log                  # Large log file
logs/                               # All log files
tmp/                                # Temporary files
.DS_Store                           # macOS artifacts
setup.py                            # Duplicate packaging config
pip-wheel-metadata/                  # Build artifacts
.pytest_cache/                       # Test cache
src/**/__pycache__/                  # Python cache
```

## Files to Move/Reorganize

```
run_tests.sh → scripts/run_tests.sh
config/sldl.conf → examples/sldl.conf.example
toolcrate.conf → examples/toolcrate.conf.example
playlists.txt → examples/playlists.txt (if keeping)
download_s7_tracks.sh → examples/download_playlist_example.sh (if keeping)
```

## Benefits of This Cleanup

1. **Cleaner Git History**: No large binary files or credential leaks
2. **Easier Installation**: Single command installation process
3. **Better Security**: No credentials in version control
4. **Simpler Maintenance**: Fork management through submodules
5. **Professional Structure**: Standard Python package layout
6. **Reduced Size**: Remove duplicate repositories and logs

## Next Steps

1. Create forks of the external repositories
2. Backup any important data from files to be deleted
3. Execute the cleanup plan in phases
4. Test installation process after each phase
5. Update documentation to reflect new structure

This cleanup will transform the project from a development workspace into a professional, distributable Python package suitable for public GitHub hosting. 