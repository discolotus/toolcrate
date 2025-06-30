# ToolCrate Makefile - Streamlined Version

.PHONY: help setup install init-config config config-validate config-show config-check-mounts wishlist-init wishlist-test wishlist-run wishlist-status configure-opus cron-add-wishlist

# Default target
help:
	@echo "ToolCrate Commands"
	@echo "=================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup                    - Install Poetry and setup project with dev dependencies"
	@echo "  make install [TARGET=local]   - Install dependencies (TARGET: local|global|pipx|docker)"
	@echo ""
	@echo "Configuration:"
	@echo "  make init-config              - Run interactive configuration setup (first time)"
	@echo "  make config                   - Update tool configs from YAML (regenerate + check mounts)"
	@echo "  make config-validate          - Validate existing configuration"
	@echo "  make config-show              - Show current configuration"
	@echo "  make config-check-mounts      - Check mount changes and rebuild containers"
	@echo ""
	@echo "Wishlist Management:"
	@echo "  make wishlist-init            - Create blank wishlist.txt file"
	@echo "  make wishlist-test            - Test wishlist processing without scheduling"
	@echo "  make wishlist-run [VERBOSE=1] - Run wishlist processing (add VERBOSE=1 for detailed output)"
	@echo "  make wishlist-status          - Show wishlist run status, logs, and summary"
	@echo ""
	@echo "Audio Configuration:"
	@echo "  make configure-opus FORMAT=flac              - Configure opus → FLAC (lossless)"
	@echo "  make configure-opus FORMAT=aac BITRATE=256   - Configure opus → AAC 256kbps"
	@echo "  make configure-opus FORMAT=aac BITRATE=320   - Configure opus → AAC 320kbps"
	@echo ""
	@echo "Automation:"
	@echo "  make cron-add-wishlist        - Add wishlist processing to cron schedule"
	@echo ""
	@echo "Examples:"
	@echo "  make setup                    # Initial project setup"
	@echo "  make init-config              # Configure for first time"
	@echo "  make install TARGET=global    # Install globally"
	@echo "  make wishlist-run VERBOSE=1   # Run wishlist with verbose output"
	@echo ""
	@echo "Note: Use 'nox' for testing and code quality commands"

# Setup Poetry and project
setup:
	@echo "Setting up Poetry and project..."
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
	fi
	poetry install --with dev
	@echo "✅ Setup complete!"
	@echo "💡 Use 'poetry run <command>' or 'make <target>' for commands."

# Install dependencies with different targets
install:
	@echo "Installing dependencies..."
	@if [ "$(TARGET)" = "global" ]; then \
		echo "Installing ToolCrate globally..."; \
		pip install --user -e .; \
		./install_global.sh; \
		echo "✅ ToolCrate installed globally!"; \
		echo "💡 The 'toolcrate' command should now be available from anywhere."; \
	elif [ "$(TARGET)" = "pipx" ]; then \
		echo "Installing ToolCrate with pipx..."; \
		if ! command -v pipx >/dev/null 2>&1; then \
			echo "❌ pipx not found. Install with: pip install --user pipx"; \
			echo "   Then run: pipx ensurepath"; \
			exit 1; \
		fi; \
		pipx install -e .; \
		echo "✅ ToolCrate installed with pipx!"; \
	elif [ "$(TARGET)" = "docker" ]; then \
		echo "Installing ToolCrate in Docker/container environment..."; \
		pip install --break-system-packages -e .; \
		echo "✅ ToolCrate installed in container!"; \
	else \
		echo "Installing with Poetry (local development)..."; \
		poetry install; \
		echo "✅ Local installation complete!"; \
	fi

# Configuration management commands

# Initial configuration setup (interactive)
init-config:
	@echo "Running ToolCrate initial configuration setup..."
	./configure_toolcrate.sh

# Update tool configurations from YAML (regenerate configs + check mounts)
config:
	@echo "Updating tool configurations from YAML..."
	@if [ ! -f "config/toolcrate.yaml" ]; then \
		echo "❌ No configuration found. Run 'make init-config' first."; \
		exit 1; \
	fi
	poetry run python -m toolcrate.config.manager check-mounts
	poetry run python -m toolcrate.config.manager generate-sldl
	poetry run python -m toolcrate.config.manager generate-wishlist-sldl
	poetry run python -m toolcrate.config.manager generate-docker
	@echo "✅ Tool configurations updated from config/toolcrate.yaml"

config-validate:
	@echo "Validating ToolCrate configuration..."
	poetry run python -m toolcrate.config.manager validate

config-show:
	@echo "Showing current ToolCrate configuration..."
	poetry run python -m toolcrate.config.manager show

config-check-mounts:
	@echo "Checking for mount path changes and rebuilding containers if needed..."
	poetry run python -m toolcrate.config.manager check-mounts

# Wishlist commands
wishlist-init:
	@echo "Creating blank wishlist.txt file..."
	@if [ ! -f "config/wishlist.txt" ]; then \
		mkdir -p config; \
		echo "# ToolCrate Wishlist File" > config/wishlist.txt; \
		echo "# Add playlist URLs or search terms, one per line" >> config/wishlist.txt; \
		echo "# Examples:" >> config/wishlist.txt; \
		echo "# https://open.spotify.com/playlist/your-playlist-id" >> config/wishlist.txt; \
		echo "# https://youtube.com/playlist?list=your-playlist-id" >> config/wishlist.txt; \
		echo '# "Artist Name - Song Title"' >> config/wishlist.txt; \
		echo '# artist:"Artist Name" album:"Album Name"' >> config/wishlist.txt; \
		echo "" >> config/wishlist.txt; \
		echo "✅ Created blank wishlist.txt file at config/wishlist.txt"; \
	else \
		echo "⚠️  wishlist.txt already exists at config/wishlist.txt"; \
	fi

wishlist-test:
	@echo "Testing wishlist processing..."
	poetry run toolcrate schedule test

wishlist-run:
	@echo "Running wishlist processing..."
	@if ! docker ps | grep -q "sldl"; then \
		echo "Docker container 'sldl' is not running. Rebuilding and starting containers..."; \
		docker-compose -f config/docker-compose.yml up -d --build; \
	else \
		echo "Docker container 'sldl' is running."; \
	fi
	@if [ "$(VERBOSE)" = "1" ]; then \
		echo "Running with verbose output..."; \
		poetry run python -m toolcrate.wishlist.processor --verbose; \
	else \
		poetry run python -m toolcrate.wishlist.processor; \
	fi

wishlist-status:
	@echo "=== Wishlist Status & Summary ==="
	@echo ""
	@echo "Recent logs:"
	poetry run toolcrate wishlist-run logs || echo "No recent logs available"
	@echo ""
	@echo "Current status:"
	poetry run toolcrate wishlist-run status || echo "Status not available"

# Consolidated opus transcoding configuration
configure-opus:
	@if [ -z "$(FORMAT)" ]; then \
		echo "Usage: make configure-opus FORMAT=<format> [BITRATE=<bitrate>]"; \
		echo ""; \
		echo "Available formats:"; \
		echo "  FORMAT=flac              - Lossless FLAC (~70-90MB/track)"; \
		echo "  FORMAT=aac BITRATE=256   - AAC 256kbps (~6-10MB/track)"; \
		echo "  FORMAT=aac BITRATE=320   - AAC 320kbps (~8-12MB/track)"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make configure-opus FORMAT=flac"; \
		echo "  make configure-opus FORMAT=aac BITRATE=256"; \
		echo ""; \
		echo "Current configuration:"; \
		grep -A 10 "post_processing:" config/toolcrate.yaml 2>/dev/null | head -10 || echo "No configuration found"; \
		exit 1; \
	fi
	@if [ "$(FORMAT)" = "flac" ]; then \
		echo "Configuring opus transcoding to FLAC (lossless, large files)..."; \
		poetry run python scripts/configure-opus-transcoding.py flac; \
	elif [ "$(FORMAT)" = "aac" ]; then \
		if [ -z "$(BITRATE)" ]; then \
			echo "❌ BITRATE required for AAC format. Use BITRATE=256 or BITRATE=320"; \
			exit 1; \
		fi; \
		echo "Configuring opus transcoding to AAC $(BITRATE)kbps..."; \
		poetry run python scripts/configure-opus-transcoding.py aac $(BITRATE); \
	else \
		echo "❌ Invalid FORMAT. Use FORMAT=flac or FORMAT=aac"; \
		exit 1; \
	fi

# Cron management
cron-add-wishlist:
	@echo "Adding wishlist processing to cron schedule..."
	poetry run python -c "from toolcrate.scripts.cron_manager import add_download_wishlist_cron; add_download_wishlist_cron()"


