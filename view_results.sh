#!/bin/bash
# THSR-Sniper Results Viewer - Docker Container Script
# This script runs the direct results viewer inside the Docker containers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME=""
EXEC_ARGS=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --details             Show detailed task information"
    echo "  --task-id ID          Show specific task details"
    echo "  --user USER_ID        Filter tasks by user ID"
    echo "  --status STATUS       Filter tasks by status (pending/running/success/failed/cancelled/expired)"
    echo "  --container NAME      Docker container name (default: auto-detect)"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Show task summary"
    echo "  $0 --details                # Show detailed information for all tasks"
    echo "  $0 --task-id abc123         # Show specific task"
    echo "  $0 --user 1 --details       # Show detailed tasks for user 1"
    echo "  $0 --status success         # Show only successful tasks"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --details)
            EXEC_ARGS="$EXEC_ARGS --details"
            shift
            ;;
        --task-id)
            EXEC_ARGS="$EXEC_ARGS --task-id $2"
            shift 2
            ;;
        --user)
            EXEC_ARGS="$EXEC_ARGS --user $2"
            shift 2
            ;;
        --status)
            EXEC_ARGS="$EXEC_ARGS --status $2"
            shift 2
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Function to detect running containers
detect_container() {
    echo -e "${BLUE}Detecting THSR-Sniper containers...${NC}"
    
    # Try to find containers in order of preference (auth first for DB access)
    local containers=(
        "thsr-sniper-auth"
        "thsr-sniper-api"
        "thsr-sniper"
        "thsr-sniper-scheduler"
    )
    
    for container in "${containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            echo -e "${GREEN}Found container: $container${NC}"
            CONTAINER_NAME="$container"
            return 0
        fi
    done
    
    # Try pattern matching as fallback
    local api_container=$(docker ps --format "{{.Names}}" | grep -E "(api|thsr.*sniper)" | head -1)
    local auth_container=$(docker ps --format "{{.Names}}" | grep -E "(auth)" | head -1)
    
    if [[ -n "$api_container" ]]; then
        echo -e "${GREEN}Found API-like container: $api_container${NC}"
        CONTAINER_NAME="$api_container"
        return 0
    elif [[ -n "$auth_container" ]]; then
        echo -e "${YELLOW}Found auth container: $auth_container${NC}"
        CONTAINER_NAME="$auth_container"
        return 0
    fi
    
    return 1
}

# Function to copy and run the viewer script
run_viewer() {
    local container="$1"
    local viewer_script="view_results_direct.py"
    
    echo -e "${BLUE}Copying viewer script to container: $container${NC}"
    
    # Copy the Python script to the container
    if ! docker cp "$SCRIPT_DIR/$viewer_script" "$container:/tmp/$viewer_script"; then
        echo -e "${RED}Failed to copy viewer script to container${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Running results viewer in container...${NC}"
    echo ""
    
    # Run the script inside the container
    if ! docker exec -it "$container" python3 "/tmp/$viewer_script" $EXEC_ARGS; then
        echo -e "${RED}Failed to run viewer script${NC}"
        return 1
    fi
    
    # Clean up the temporary file
    docker exec "$container" rm -f "/tmp/$viewer_script" 2>/dev/null || true
}

# Main execution
main() {
    echo -e "${GREEN}THSR-Sniper Docker Results Viewer${NC}"
    echo "=================================================="
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed or not available${NC}"
        exit 1
    fi
    
    # Check if viewer script exists
    if [[ ! -f "$SCRIPT_DIR/view_results_direct.py" ]]; then
        echo -e "${RED}Error: view_results_direct.py not found in $SCRIPT_DIR${NC}"
        echo "Please ensure the script is in the same directory as this bash script."
        exit 1
    fi
    
    # Detect or use specified container
    if [[ -z "$CONTAINER_NAME" ]]; then
        if ! detect_container; then
            echo -e "${RED}Error: No suitable THSR-Sniper containers found${NC}"
            echo "Please ensure the containers are running with 'docker compose up -d'"
            echo "Or specify a container name with --container option"
            exit 1
        fi
    else
        # Verify the specified container exists and is running
        if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${RED}Error: Container '$CONTAINER_NAME' not found or not running${NC}"
            exit 1
        fi
        echo -e "${GREEN}Using specified container: $CONTAINER_NAME${NC}"
    fi
    
    # Run the viewer
    if ! run_viewer "$CONTAINER_NAME"; then
        echo -e "${RED}Failed to run results viewer${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}Results viewer completed successfully${NC}"
}

# Run main function
main "$@"
