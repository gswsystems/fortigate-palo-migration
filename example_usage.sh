#!/bin/bash
# Example usage script for FortiGate to Palo Alto migration

# Configuration
FORTIGATE_HOST="firewall.example.com"
FORTIGATE_API_KEY="your-api-key-here"
VDOM="root"
OUTPUT_DIR="./migration_output"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}FortiGate to Palo Alto Migration Tool${NC}"
echo "========================================"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Example 1: Basic migration with shared device group
echo -e "${YELLOW}Example 1: Basic Migration${NC}"
python3 fortigate_palo_converter.py \
  --host "$FORTIGATE_HOST" \
  --api-key "$FORTIGATE_API_KEY" \
  --vdom "$VDOM" \
  --output "$OUTPUT_DIR/basic_migration.tf" \
  --save-json "$OUTPUT_DIR/basic_debug.json"

echo ""
echo -e "${GREEN}✓ Basic migration complete${NC}"
echo "  Output: $OUTPUT_DIR/basic_migration.tf"
echo ""

# Example 2: Migration with custom device group and template
echo -e "${YELLOW}Example 2: Advanced Migration with Template${NC}"
python3 fortigate_palo_converter.py \
  --host "$FORTIGATE_HOST" \
  --api-key "$FORTIGATE_API_KEY" \
  --vdom "$VDOM" \
  --device-group "Production-DG" \
  --vsys "vsys1" \
  --template "Production-Template" \
  --output "$OUTPUT_DIR/advanced_migration.tf" \
  --save-json "$OUTPUT_DIR/advanced_debug.json"

echo ""
echo -e "${GREEN}✓ Advanced migration complete${NC}"
echo "  Output: $OUTPUT_DIR/advanced_migration.tf"
echo ""

# Example 3: Using environment variables
echo -e "${YELLOW}Example 3: Using Environment Variables${NC}"
export FORTIGATE_HOST="$FORTIGATE_HOST"
export FORTIGATE_API_KEY="$FORTIGATE_API_KEY"
export FORTIGATE_VDOM="$VDOM"

python3 fortigate_palo_converter.py \
  --device-group "Test-DG" \
  --output "$OUTPUT_DIR/env_migration.tf"

echo ""
echo -e "${GREEN}✓ Environment variable migration complete${NC}"
echo "  Output: $OUTPUT_DIR/env_migration.tf"
echo ""

# Summary
echo "========================================"
echo -e "${GREEN}Migration Summary${NC}"
echo "========================================"
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Generated files:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Review generated Terraform files"
echo "  2. cd $OUTPUT_DIR"
echo "  3. terraform init"
echo "  4. terraform plan"
echo "  5. terraform apply"
echo ""
echo -e "${YELLOW}Note: Manual review required for:${NC}"
echo "  - Zone assignments"
echo "  - ICMP service objects"
echo "  - Security profiles"
echo "  - Application-based policies"
