#!/usr/bin/env python3
"""
Migration Verification Script

Verifies that the enhanced models database migration was applied correctly.
Checks enum types, columns, indexes, and data integrity.
"""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_enum_types(connection):
    """Verify that all enhanced enum types exist"""
    logger.info("Checking enhanced enum types...")
    
    expected_enums = ['taskexecutionstatus', 'progressstatus', 'recurrencecycle', 'plansource']
    
    result = connection.execute("""
        SELECT typname FROM pg_type 
        WHERE typname IN ('taskexecutionstatus', 'progressstatus', 'recurrencecycle', 'plansource')
        ORDER BY typname
    """).fetchall()
    
    found_enums = [row[0] for row in result]
    
    for enum_name in expected_enums:
        if enum_name in found_enums:
            logger.info(f"✅ Enum type '{enum_name}' exists")
        else:
            logger.error(f"❌ Enum type '{enum_name}' missing")
            return False
    
    return True


def verify_columns(connection):
    """Verify that all enhanced columns exist"""
    logger.info("Checking enhanced columns...")
    
    expected_columns = [
        ('tasks', 'execution_status'),
        ('tasks', 'progress_status'),
        ('tasks', 'recurrence_cycle'),
        ('tasks', 'execution_metadata'),
        ('plans', 'plan_source'),
        ('plans', 'plan_metadata'),
        ('feedback', 'feedback_data')
    ]
    
    all_columns_exist = True
    
    for table_name, column_name in expected_columns:
        result = connection.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """).fetchone()
        
        if result:
            logger.info(f"✅ Column '{table_name}.{column_name}' exists")
        else:
            logger.error(f"❌ Column '{table_name}.{column_name}' missing")
            all_columns_exist = False
    
    return all_columns_exist


def verify_indexes(connection):
    """Verify that performance indexes exist"""
    logger.info("Checking performance indexes...")
    
    expected_indexes = [
        'idx_task_execution_composite',
        'idx_task_progress_composite',
        'idx_task_recurrence_composite',
        'idx_plan_source_composite',
        'idx_scheduled_task_composite',
        'idx_feedback_analysis_composite',
        'idx_user_goal_performance',
        'idx_task_priority_status',
        'idx_weekly_planning'
    ]
    
    all_indexes_exist = True
    
    for index_name in expected_indexes:
        result = connection.execute(f"""
            SELECT indexname FROM pg_indexes 
            WHERE indexname = '{index_name}'
        """).fetchone()
        
        if result:
            logger.info(f"✅ Index '{index_name}' exists")
        else:
            logger.error(f"❌ Index '{index_name}' missing")
            all_indexes_exist = False
    
    return all_indexes_exist


def verify_data_integrity(connection):
    """Verify data integrity after migration"""
    logger.info("Checking data integrity...")
    
    try:
        # Check that existing tasks have non-null enum values
        result = connection.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE execution_status IS NULL OR progress_status IS NULL OR recurrence_cycle IS NULL
        """).fetchone()
        
        null_count = result[0] if result else 0
        
        if null_count == 0:
            logger.info("✅ All tasks have non-null enum values")
        else:
            logger.error(f"❌ Found {null_count} tasks with null enum values")
            return False
        
        # Check that existing plans have non-null plan_source
        result = connection.execute("""
            SELECT COUNT(*) FROM plans WHERE plan_source IS NULL
        """).fetchone()
        
        null_plan_source = result[0] if result else 0
        
        if null_plan_source == 0:
            logger.info("✅ All plans have non-null plan_source")
        else:
            logger.error(f"❌ Found {null_plan_source} plans with null plan_source")
            return False
        
        # Verify enum constraints work
        try:
            connection.execute("""
                INSERT INTO tasks (title, execution_status, progress_status, recurrence_cycle, user_id) 
                VALUES ('test_invalid_enum', 'invalid_status', 'not_started', 'none', 1)
            """)
            connection.rollback()
            logger.error("❌ Enum constraint not working - invalid value was accepted")
            return False
        except Exception:
            # This is expected - invalid enum value should be rejected
            connection.rollback()
            logger.info("✅ Enum constraints working correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data integrity check failed: {e}")
        return False


def verify_performance(connection):
    """Check that indexes are being used for queries"""
    logger.info("Checking query performance...")
    
    try:
        # Test query that should use the composite index
        result = connection.execute("""
            EXPLAIN (FORMAT JSON) 
            SELECT * FROM tasks 
            WHERE user_id = 1 AND execution_status = 'in_progress' 
            ORDER BY created_at
        """).fetchone()
        
        explain_json = result[0]
        
        # Check if index scan is being used (simplified check)
        if "Index Scan" in str(explain_json) or "Bitmap" in str(explain_json):
            logger.info("✅ Composite indexes are being used by query planner")
        else:
            logger.warning("⚠️ Query planner may not be using indexes optimally")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance check failed: {e}")
        return False


def main():
    """Main verification function"""
    logger.info("🔍 Starting migration verification...")
    
    try:
        from app.db import engine
        
        with engine.connect() as connection:
            checks = [
                ("Enum Types", verify_enum_types),
                ("Columns", verify_columns),
                ("Indexes", verify_indexes),
                ("Data Integrity", verify_data_integrity),
                ("Performance", verify_performance)
            ]
            
            all_checks_passed = True
            
            for check_name, check_func in checks:
                logger.info(f"\n--- {check_name} Verification ---")
                try:
                    if check_func(connection):
                        logger.info(f"✅ {check_name} verification PASSED")
                    else:
                        logger.error(f"❌ {check_name} verification FAILED")
                        all_checks_passed = False
                except Exception as e:
                    logger.error(f"❌ {check_name} verification FAILED with exception: {e}")
                    all_checks_passed = False
            
            logger.info(f"\n{'='*50}")
            if all_checks_passed:
                logger.info("🎉 ALL MIGRATION VERIFICATIONS PASSED!")
                logger.info("✅ Enhanced models migration successful")
                logger.info("✅ Database is ready for enhanced features")
            else:
                logger.error("❌ SOME MIGRATION VERIFICATIONS FAILED!")
                logger.error("⚠️ Please review the errors above")
                logger.error("💡 Consider rolling back and re-running migration")
            
            return all_checks_passed
            
    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
