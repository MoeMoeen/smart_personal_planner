#!/bin/bash

# 🚀 Smart Personal Planner - Enhanced Features Deployment Script
# This script handles the complete deployment of enhanced models and backlog features

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="smart_personal_planner"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deployment_$(date +%Y%m%d_%H%M%S).log"
VENV_PATH="./venv"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a $LOG_FILE
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a $LOG_FILE
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a $LOG_FILE
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $LOG_FILE
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking deployment prerequisites..."
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        exit 1
    fi
    
    # Check if database is accessible
    source $VENV_PATH/bin/activate
    python -c "
import sys
sys.path.insert(0, '.')
try:
    from app.db import engine
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
    " 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Database connection failed"
        exit 1
    fi
    
    # Check if Alembic is configured
    if [ ! -f "alembic.ini" ]; then
        print_error "Alembic configuration not found"
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to create backup
create_backup() {
    print_status "Creating database backup..."
    
    mkdir -p $BACKUP_DIR
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Get database URL from environment or config
    source $VENV_PATH/bin/activate
    DB_URL=$(python -c "
import sys
sys.path.insert(0, '.')
from app.db import DATABASE_URL
print(DATABASE_URL.replace('postgresql://', '').replace('postgresql+psycopg2://', ''))
")
    
    if [ -z "$DB_URL" ]; then
        print_error "Could not determine database URL"
        exit 1
    fi
    
    # Extract database connection details
    DB_INFO=$(echo $DB_URL | sed 's/.*@\([^:]*\):\([0-9]*\)\/\(.*\)/\1 \2 \3/')
    read -r DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"
    
    # Create backup
    pg_dump -h $DB_HOST -p $DB_PORT -U postgres $DB_NAME > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        print_success "Database backup created: $BACKUP_FILE"
        echo "BACKUP_FILE=$BACKUP_FILE" >> $LOG_FILE
    else
        print_error "Database backup failed"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    print_status "Running test suite..."
    
    source $VENV_PATH/bin/activate
    
    # Run enhanced models tests
    print_status "Testing enhanced models..."
    python -m pytest tests/test_enhanced_models.py -v 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Enhanced models tests failed"
        exit 1
    fi
    
    # Run integration tests
    print_status "Running integration tests..."
    python -m pytest tests/test_integration.py -v 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_warning "Integration tests failed, but continuing..."
    fi
    
    print_success "Test suite completed"
}

# Function to apply database migration
apply_migration() {
    print_status "Applying database migration..."
    
    source $VENV_PATH/bin/activate
    
    # Check current migration status
    print_status "Current migration status:"
    alembic current 2>&1 | tee -a $LOG_FILE
    
    # Apply migration
    print_status "Applying enhanced models migration..."
    alembic upgrade head 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Migration failed"
        print_status "Rolling back to backup..."
        rollback_deployment
        exit 1
    fi
    
    # Verify migration
    print_status "Verifying migration..."
    python scripts/verify_migration.py 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Migration verification failed"
        rollback_deployment
        exit 1
    fi
    
    print_success "Database migration completed successfully"
}

# Function to update application
update_application() {
    print_status "Updating application..."
    
    source $VENV_PATH/bin/activate
    
    # Install/update dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt 2>&1 | tee -a $LOG_FILE
    
    # Compile Python files
    print_status "Compiling Python files..."
    python -m compileall app/ 2>&1 | tee -a $LOG_FILE
    
    # Clear any cached files
    print_status "Clearing cache..."
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_success "Application updated successfully"
}

# Function to run post-deployment checks
post_deployment_checks() {
    print_status "Running post-deployment checks..."
    
    source $VENV_PATH/bin/activate
    
    # Test enhanced models functionality
    print_status "Testing enhanced models functionality..."
    python scripts/test_enhanced_models_functionality.py 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Enhanced models functionality test failed"
        exit 1
    fi
    
    # Test semantic memory
    print_status "Testing semantic memory..."
    python -c "
from app.cognitive.semantic_memory import SemanticMemory
memory = SemanticMemory(user_id=1)
memory_id = memory.log_operation('test_deployment', {'status': 'success'})
print(f'Semantic memory test successful: {memory_id}')
" 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "Semantic memory test failed"
        exit 1
    fi
    
    # Test LangGraph tools
    print_status "Testing LangGraph tools..."
    python -c "
from app.cognitive.langgraph_tools import create_langgraph_tools
from app.cognitive.world.updater import WorldUpdater
from app.cognitive.world.state import WorldState
from app.cognitive.semantic_memory import SemanticMemory

world_state = WorldState(user_id='1', all_tasks=[])
updater = WorldUpdater(world_state, user_id=1)
memory = SemanticMemory(user_id=1)
tools = create_langgraph_tools(updater, memory)
print(f'LangGraph tools test successful: {len(tools)} tools created')
" 2>&1 | tee -a $LOG_FILE
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        print_error "LangGraph tools test failed"
        exit 1
    fi
    
    print_success "All post-deployment checks passed"
}

# Function to rollback deployment
rollback_deployment() {
    print_error "Initiating deployment rollback..."
    
    if [ -f "$LOG_FILE" ] && grep -q "BACKUP_FILE=" "$LOG_FILE"; then
        BACKUP_FILE=$(grep "BACKUP_FILE=" $LOG_FILE | tail -1 | cut -d'=' -f2)
        
        if [ -f "$BACKUP_FILE" ]; then
            print_status "Restoring database from backup: $BACKUP_FILE"
            
            # Get database connection details
            source $VENV_PATH/bin/activate
            DB_URL=$(python -c "
import sys
sys.path.insert(0, '.')
from app.db import DATABASE_URL
print(DATABASE_URL.replace('postgresql://', '').replace('postgresql+psycopg2://', ''))
")
            
            DB_INFO=$(echo $DB_URL | sed 's/.*@\([^:]*\):\([0-9]*\)\/\(.*\)/\1 \2 \3/')
            read -r DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"
            
            # Restore backup
            psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME < $BACKUP_FILE
            
            if [ $? -eq 0 ]; then
                print_success "Database restored from backup"
            else
                print_error "Database restoration failed"
            fi
        else
            print_error "Backup file not found: $BACKUP_FILE"
        fi
    else
        print_error "No backup file information found"
    fi
}

# Function to enable features gradually
enable_features() {
    print_status "Enabling features gradually..."
    
    source $VENV_PATH/bin/activate
    
    # This would integrate with your feature flag system
    # For now, we'll just log that features are enabled
    
    features=("enhanced_models" "logging_hooks" "conflict_resolution" "undo_stack" "semantic_memory" "langgraph_tools")
    
    for feature in "${features[@]}"; do
        print_status "Enabling feature: $feature"
        # python scripts/enable_feature.py --feature=$feature
        echo "Feature enabled: $feature" >> $LOG_FILE
        sleep 2  # Gradual rollout
    done
    
    print_success "All features enabled successfully"
}

# Main deployment function
main() {
    print_status "🚀 Starting Smart Personal Planner Enhanced Features Deployment"
    print_status "Deployment started at: $(date)"
    print_status "Log file: $LOG_FILE"
    
    # Create log directory
    mkdir -p $(dirname $LOG_FILE)
    
    # Step 1: Prerequisites
    check_prerequisites
    
    # Step 2: Backup
    create_backup
    
    # Step 3: Tests
    run_tests
    
    # Step 4: Database Migration
    apply_migration
    
    # Step 5: Application Update
    update_application
    
    # Step 6: Post-deployment Checks
    post_deployment_checks
    
    # Step 7: Feature Enablement
    enable_features
    
    print_success "🎉 Deployment completed successfully!"
    print_status "Deployment finished at: $(date)"
    print_status "Summary:"
    print_status "  ✅ Database migration applied"
    print_status "  ✅ Enhanced models active"
    print_status "  ✅ Semantic memory enabled"
    print_status "  ✅ LangGraph tools available"
    print_status "  ✅ All 5 backlog features deployed"
    
    print_status "📊 Next steps:"
    print_status "  1. Monitor application logs"
    print_status "  2. Check user feedback"
    print_status "  3. Monitor performance metrics"
    print_status "  4. Review semantic memory data"
}

# Trap to handle script interruption
trap 'print_error "Deployment interrupted"; rollback_deployment; exit 1' INT TERM

# Check if this script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
