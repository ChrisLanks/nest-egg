#!/bin/bash
###############################################################################
# Nest Egg - Production Setup
#
# Interactive helper that walks you through creating a production .env.docker
# file from the template, generates secure keys, and validates the result.
#
# Usage: ./scripts/prod/setup.sh [options]
#
# Options:
#   --check    Validate an existing .env.docker without modifying it
#   --help     Show this help message
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ENV_FILE=".env.docker"
TEMPLATE=".env.docker.example"

CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --check)  CHECK_ONLY=true; shift ;;
        --help)   head -n 13 "$0" | tail -n 11; exit 0 ;;
        *)        echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

###############################################################################
# Helpers
###############################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}⚠${NC} $1"; }
print_error()   { echo -e "  ${RED}✗${NC} $1"; }
print_info()    { echo -e "  ${BLUE}ℹ${NC} $1"; }

generate_key() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        python3 -c "import secrets; print(secrets.token_hex(32))"
    fi
}

# Read a value from the env file
env_val() {
    grep "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d'=' -f2-
}

###############################################################################
# Validation
###############################################################################

validate_env() {
    print_header "Validating $ENV_FILE"

    local errors=0
    local warnings=0

    # Required keys that must not be default/empty
    local required_keys=(
        "SECRET_KEY"
        "MASTER_ENCRYPTION_KEY"
        "POSTGRES_PASSWORD"
    )

    for key in "${required_keys[@]}"; do
        local val
        val=$(env_val "$key")
        if [ -z "$val" ] || [[ "$val" == *"CHANGE_ME"* ]]; then
            print_error "$key is not set (still default)"
            errors=$((errors + 1))
        else
            print_success "$key is set"
        fi
    done

    # ALLOWED_HOSTS must not be wildcard
    local hosts
    hosts=$(env_val "ALLOWED_HOSTS")
    if [ -z "$hosts" ] || [ "$hosts" = "*" ] || [[ "$hosts" == *"localhost"* ]]; then
        print_error "ALLOWED_HOSTS should be set to your production domain(s), not '$hosts'"
        errors=$((errors + 1))
    else
        print_success "ALLOWED_HOSTS = $hosts"
    fi

    # CORS_ORIGINS should not contain localhost in prod
    local cors
    cors=$(env_val "CORS_ORIGINS")
    if [[ "$cors" == *"localhost"* ]]; then
        print_warning "CORS_ORIGINS contains localhost — update for production"
        warnings=$((warnings + 1))
    else
        print_success "CORS_ORIGINS = $cors"
    fi

    # ENVIRONMENT should be production
    local env
    env=$(env_val "ENVIRONMENT")
    if [ "$env" != "production" ]; then
        print_warning "ENVIRONMENT is '$env' (expected 'production')"
        warnings=$((warnings + 1))
    else
        print_success "ENVIRONMENT = production"
    fi

    # DEBUG should be false
    local debug
    debug=$(env_val "DEBUG")
    if [ "$debug" = "true" ]; then
        print_error "DEBUG=true — must be false in production"
        errors=$((errors + 1))
    else
        print_success "DEBUG = false"
    fi

    # FLOWER_PASSWORD
    local flower_pw
    flower_pw=$(env_val "FLOWER_PASSWORD")
    if [ -z "$flower_pw" ] || [[ "$flower_pw" == *"CHANGE_ME"* ]]; then
        print_warning "FLOWER_PASSWORD is not set"
        warnings=$((warnings + 1))
    else
        print_success "FLOWER_PASSWORD is set"
    fi

    # Banking providers — informational
    local plaid_enabled teller_enabled
    plaid_enabled=$(env_val "PLAID_ENABLED")
    teller_enabled=$(env_val "TELLER_ENABLED")
    if [ "$plaid_enabled" = "true" ]; then
        local pid
        pid=$(env_val "PLAID_CLIENT_ID")
        if [ -z "$pid" ] || [[ "$pid" == *"your_"* ]]; then
            print_warning "PLAID_ENABLED=true but PLAID_CLIENT_ID looks like a placeholder"
            warnings=$((warnings + 1))
        else
            print_success "Plaid configured"
        fi
    fi
    if [ "$teller_enabled" = "true" ]; then
        local tid
        tid=$(env_val "TELLER_APP_ID")
        if [ -z "$tid" ] || [[ "$tid" == *"your_"* ]]; then
            print_warning "TELLER_ENABLED=true but TELLER_APP_ID looks like a placeholder"
            warnings=$((warnings + 1))
        else
            print_success "Teller configured"
        fi
    fi

    echo ""
    if [ $errors -gt 0 ]; then
        echo -e "  ${RED}${BOLD}$errors error(s)${NC}, $warnings warning(s)"
        echo -e "  ${RED}Fix errors before deploying.${NC}"
        return 1
    elif [ $warnings -gt 0 ]; then
        echo -e "  ${GREEN}0 errors${NC}, ${YELLOW}$warnings warning(s)${NC}"
        echo -e "  ${YELLOW}Review warnings before deploying.${NC}"
        return 0
    else
        echo -e "  ${GREEN}${BOLD}All checks passed!${NC}"
        return 0
    fi
}

###############################################################################
# Interactive Setup
###############################################################################

interactive_setup() {
    print_header "Nest Egg — Production Environment Setup"

    if [ ! -f "$TEMPLATE" ]; then
        echo -e "${RED}Template $TEMPLATE not found. Run from the project root.${NC}"
        exit 1
    fi

    if [ -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}$ENV_FILE already exists.${NC}"
        read -p "  Overwrite? (y/N): " -n 1 -r; echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "  Keeping existing file. Running validation..."
            validate_env
            return
        fi
    fi

    cp "$TEMPLATE" "$ENV_FILE"
    echo -e "${GREEN}Created $ENV_FILE from template${NC}\n"

    # --- Generate secrets ---
    echo -e "${BOLD}Generating secure keys...${NC}"
    local secret_key master_key pg_password flower_pw
    secret_key=$(generate_key)
    master_key=$(generate_key)
    pg_password=$(generate_key | head -c 32)
    flower_pw=$(generate_key | head -c 16)

    sed -i "s|CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32|REPLACE_PLACEHOLDER|" "$ENV_FILE"
    # Replace first occurrence (SECRET_KEY)
    sed -i "0,/REPLACE_PLACEHOLDER/s|REPLACE_PLACEHOLDER|$secret_key|" "$ENV_FILE"
    # Replace second occurrence (MASTER_ENCRYPTION_KEY)
    sed -i "0,/REPLACE_PLACEHOLDER/s|REPLACE_PLACEHOLDER|$master_key|" "$ENV_FILE"
    sed -i "s|CHANGE_ME_GENERATE_STRONG_PASSWORD|$pg_password|" "$ENV_FILE"
    sed -i "s|CHANGE_ME_SECURE_PASSWORD|$flower_pw|" "$ENV_FILE"
    print_success "SECRET_KEY generated"
    print_success "MASTER_ENCRYPTION_KEY generated"
    print_success "POSTGRES_PASSWORD generated"
    print_success "FLOWER_PASSWORD generated"

    # --- Domain ---
    echo ""
    echo -e "${BOLD}Domain Configuration${NC}"
    echo -e "  Enter your production domain (e.g. app.nestegg.com)"
    read -p "  Domain: " domain
    if [ -n "$domain" ]; then
        sed -i "s|app.yourdomain.com,api.yourdomain.com|$domain|" "$ENV_FILE"
        sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://$domain|" "$ENV_FILE"
        sed -i "s|VITE_API_URL=.*|VITE_API_URL=https://$domain|" "$ENV_FILE"
        print_success "Domain set to $domain"
    else
        print_warning "Skipped — update ALLOWED_HOSTS and CORS_ORIGINS manually"
    fi

    # --- Banking providers ---
    echo ""
    echo -e "${BOLD}Banking Providers (optional — press Enter to skip)${NC}"
    echo ""
    echo -e "  ${BLUE}Plaid${NC} — 11,000+ institutions (sign up: https://dashboard.plaid.com)"
    read -p "  Plaid Client ID: " plaid_id
    if [ -n "$plaid_id" ]; then
        read -p "  Plaid Secret: " plaid_secret
        read -p "  Plaid Env [sandbox/development/production]: " plaid_env
        plaid_env=${plaid_env:-sandbox}
        sed -i "s|PLAID_CLIENT_ID=.*|PLAID_CLIENT_ID=$plaid_id|" "$ENV_FILE"
        sed -i "s|PLAID_SECRET=.*|PLAID_SECRET=$plaid_secret|" "$ENV_FILE"
        sed -i "s|PLAID_ENV=.*|PLAID_ENV=$plaid_env|" "$ENV_FILE"
        print_success "Plaid configured"
    else
        sed -i "s|PLAID_ENABLED=true|PLAID_ENABLED=false|" "$ENV_FILE"
        print_info "Plaid disabled"
    fi

    echo ""
    echo -e "  ${BLUE}Teller${NC} — 100 free accounts/month (sign up: https://teller.io)"
    read -p "  Teller App ID: " teller_id
    if [ -n "$teller_id" ]; then
        read -p "  Teller API Key: " teller_key
        read -p "  Teller Env [sandbox/production]: " teller_env
        teller_env=${teller_env:-sandbox}
        sed -i "s|TELLER_APP_ID=.*|TELLER_APP_ID=$teller_id|" "$ENV_FILE"
        sed -i "s|TELLER_API_KEY=.*|TELLER_API_KEY=$teller_key|" "$ENV_FILE"
        sed -i "s|TELLER_ENV=.*|TELLER_ENV=$teller_env|" "$ENV_FILE"
        print_success "Teller configured"
    else
        sed -i "s|TELLER_ENABLED=true|TELLER_ENABLED=false|" "$ENV_FILE"
        print_info "Teller disabled"
    fi

    # --- Validate ---
    echo ""
    validate_env

    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    echo -e "  1. Review ${YELLOW}$ENV_FILE${NC} and adjust any remaining settings"
    echo -e "  2. Run: ${YELLOW}./scripts/prod/run.sh${NC}"
    echo -e "  3. See ${YELLOW}DEPLOYMENT.md${NC} and ${YELLOW}SELF_HOSTING.md${NC} for full guides"
    echo ""
}

###############################################################################
# Main
###############################################################################

if $CHECK_ONLY; then
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}$ENV_FILE not found. Run ./scripts/prod/setup.sh first.${NC}"
        exit 1
    fi
    validate_env
else
    interactive_setup
fi
