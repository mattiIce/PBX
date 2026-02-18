#!/bin/bash
###############################################################################
# Enable FIPS 140-2 Mode on Ubuntu Server
# This script configures Ubuntu for FIPS 140-2 compliance
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================================================="
echo "FIPS 140-2 Enablement Script for Ubuntu"
echo "=============================================================================="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Detect Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo -e "${RED}Cannot detect Ubuntu version${NC}"
    exit 1
fi

echo "Detected OS: $OS $VER"
echo ""

# Check if Ubuntu Pro is available (Ubuntu 20.04+ supports FIPS)
if ! command -v ua &> /dev/null; then
    echo -e "${YELLOW}Ubuntu Pro client (ua) not found. Installing...${NC}"
    apt-get update
    apt-get install -y ubuntu-advantage-tools
fi

echo ""
echo "=============================================================================="
echo "FIPS Enablement Options"
echo "=============================================================================="
echo ""
echo "Ubuntu provides FIPS 140-2 validated cryptographic modules through Ubuntu Pro."
echo "There are two ways to enable FIPS:"
echo ""
echo "1. Ubuntu Pro FIPS (Recommended - fully validated)"
echo "   - Requires Ubuntu Pro subscription (free for personal use, up to 5 machines)"
echo "   - Provides NIST-validated FIPS 140-2 Level 1 cryptographic modules"
echo "   - Command: sudo ua enable fips --assume-yes"
echo ""
echo "2. OpenSSL FIPS Module (Alternative)"
echo "   - Uses OpenSSL 3.0+ FIPS provider"
echo "   - Does not require Ubuntu Pro"
echo "   - Not formally validated but uses FIPS-approved algorithms"
echo ""

read -p "Choose option (1 for Ubuntu Pro FIPS, 2 for OpenSSL FIPS, q to quit): " choice

case $choice in
    1)
        echo ""
        echo "=============================================================================="
        echo "Enabling Ubuntu Pro FIPS"
        echo "=============================================================================="
        echo ""

        # Check if Ubuntu Pro is attached
        ua_status=$(ua status --format json 2>/dev/null | grep -o '"attached": *[^,}]*' | cut -d ':' -f2 | tr -d ' "')

        if [ "$ua_status" != "true" ]; then
            echo -e "${YELLOW}Ubuntu Pro is not attached to this system.${NC}"
            echo ""
            echo "To enable FIPS, you need to attach this system to Ubuntu Pro:"
            echo "1. Get a free Ubuntu Pro token at: https://ubuntu.com/pro"
            echo "2. Attach this system: sudo ua attach <your-token>"
            echo "3. Re-run this script"
            echo ""
            exit 1
        fi

        echo "Ubuntu Pro is attached. Enabling FIPS..."

        # Enable FIPS
        ua enable fips --assume-yes

        echo ""
        echo -e "${GREEN}✓ FIPS enabled successfully${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT: You must reboot for FIPS mode to take effect${NC}"
        echo ""
        read -p "Reboot now? (y/n): " reboot_choice
        if [ "$reboot_choice" = "y" ]; then
            reboot
        fi
        ;;

    2)
        echo ""
        echo "=============================================================================="
        echo "Configuring OpenSSL FIPS Module"
        echo "=============================================================================="
        echo ""

        # Check OpenSSL version (need 3.0+)
        openssl_version=$(openssl version | awk '{print $2}' | cut -d'.' -f1)

        if [ "$openssl_version" -lt 3 ]; then
            echo -e "${RED}OpenSSL 3.0+ is required for FIPS module${NC}"
            echo "Your version: $(openssl version)"
            echo ""
            echo "Ubuntu 22.04+ includes OpenSSL 3.0"
            echo "Consider upgrading Ubuntu or using Ubuntu Pro FIPS"
            exit 1
        fi

        echo "OpenSSL version: $(openssl version)"
        echo ""

        # Install FIPS module if available
        echo "Installing OpenSSL FIPS provider..."
        apt-get update
        apt-get install -y openssl

        # Check if FIPS module exists
        fips_module="/usr/lib/x86_64-linux-gnu/ossl-modules/fips.so"
        if [ ! -f "$fips_module" ]; then
            echo -e "${YELLOW}FIPS module not found. Installing from source...${NC}"

            # Build FIPS module
            apt-get install -y build-essential

            # Create temp directory
            tmp_dir=$(mktemp -d)
            cd "$tmp_dir"

            # Download OpenSSL source with verification
            openssl_src_version="3.0.16"
            openssl_tar="openssl-${openssl_src_version}.tar.gz"
            openssl_url="https://www.openssl.org/source/${openssl_tar}"

            echo "Downloading OpenSSL ${openssl_src_version}..."
            wget "${openssl_url}"

            # Download SHA256 checksum
            wget "${openssl_url}.sha256"

            # Verify checksum
            echo "Verifying download integrity..."
            if ! sha256sum -c "${openssl_tar}.sha256"; then
                echo -e "${RED}Checksum verification failed!${NC}"
                echo "Download may be corrupted or tampered with."
                exit 1
            fi

            echo "Checksum verified successfully"
            tar -xzf "${openssl_tar}"
            cd "openssl-${openssl_src_version}"

            # Configure with FIPS
            ./Configure enable-fips
            make -j$(nproc)

            # Install FIPS module
            make install_fips

            # Cleanup
            cd /
            rm -rf "$tmp_dir"

            echo -e "${GREEN}✓ FIPS module built and installed${NC}"
        fi

        # Configure OpenSSL to use FIPS
        echo ""
        echo "Configuring OpenSSL FIPS..."

        openssl_conf="/etc/ssl/openssl.cnf"

        # Backup original config
        cp "$openssl_conf" "${openssl_conf}.backup"

        # Add FIPS configuration
        cat >> "$openssl_conf" << 'EOF'

# FIPS Configuration
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
fips = fips_sect

[default_sect]
activate = 1

[fips_sect]
activate = 1
EOF

        # Note: /proc/sys/crypto/fips_enabled is typically read-only
        # FIPS mode must be enabled via kernel boot parameters
        echo ""
        echo "Note: FIPS mode will be enabled on next boot via kernel parameter"

        # Make it persistent via GRUB
        if ! grep -q "fips=1" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="fips=1 /' /etc/default/grub
            update-grub
        fi

        echo ""
        echo -e "${GREEN}✓ OpenSSL FIPS module configured${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT: You must reboot for FIPS mode to take effect${NC}"
        echo ""
        read -p "Reboot now? (y/n): " reboot_choice
        if [ "$reboot_choice" = "y" ]; then
            reboot
        fi
        ;;

    q)
        echo "Exiting without changes"
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "=============================================================================="
echo "Post-Reboot Verification"
echo "=============================================================================="
echo ""
echo "After rebooting, verify FIPS mode is enabled:"
echo ""
echo "1. Check kernel FIPS status:"
echo "   cat /proc/sys/crypto/fips_enabled"
echo "   (Should output: 1)"
echo ""
echo "2. Verify OpenSSL FIPS:"
echo "   openssl list -providers"
echo "   (Should show 'fips' provider)"
echo ""
echo "3. Run PBX verification script:"
echo "   cd /home/runner/work/PBX/PBX"
echo "   python3 scripts/verify_fips.py"
echo ""
