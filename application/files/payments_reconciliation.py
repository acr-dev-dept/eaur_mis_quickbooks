#!/usr/bin/env python3
"""
Wallet reconciliation CLI importer

Usage:
    ./wallet_reconciliation_import.py /path/to/file.json
    ./wallet_reconciliation_import.py /path/to/file.json --verbose
    ./wallet_reconciliation_import.py /path/to/file.json --dry-run
"""

import sys
import json
import logging
from pathlib import Path
from decimal import Decimal
import os
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from application import create_app, db
from application.models.mis_models import TblStudentWallet


# Configure logging
def setup_logging(verbose=False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"wallet_import_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Log file: {log_file}")
    return logger


def validate_transaction(txn: dict, payer_code: str) -> tuple[bool, str]:
    """Validate a single transaction record."""
    # Check transaction_reference
    txn_ref = txn.get("transaction_reference")
    if txn_ref is None or str(txn_ref).strip() == "":
        return False, f"Missing transaction_reference"
    
    # Check paid_amount
    try:
        amount = float(txn.get("paid_amount", 0))
        if amount <= 0:
            return False, f"Invalid amount {amount}"
    except (ValueError, TypeError):
        return False, f"Invalid paid_amount format: {txn.get('paid_amount')}"
    
    # slip_no is optional but should be string if present
    slip_no = txn.get("slip_no")
    if slip_no is not None and not isinstance(slip_no, str):
        return False, f"slip_no must be string, got {type(slip_no).__name__}"
    
    return True, ""


def import_wallet_transactions(json_path: str, logger: logging.Logger, dry_run=False):
    """Import wallet transactions from JSON file."""
    
    logger.info(f"Starting import from: {json_path}")
    logger.info(f"Dry run mode: {dry_run}")
    
    # Test database connection
    try:
        wallet_count = db.session.query(TblStudentWallet).count()
        logger.info(f"✓ Database connected - found {wallet_count} total wallets in database")
        
        # Show sample reg_no values
        sample_wallets = db.session.query(TblStudentWallet.reg_no).limit(5).all()
        sample_reg_nos = [w.reg_no for w in sample_wallets]
        logger.info(f"Sample reg_no values: {sample_reg_nos}")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise
    
    with open(json_path, "r") as f:
        data = json.load(f)

    per_payer_code = data.get("per_payer_code", {})
    total_payers = len(per_payer_code)
    
    logger.info(f"Found {total_payers} payer codes to process")

    results = {
        "updated": [],
        "created": [],
        "failed": [],
        "skipped": []
    }

    processed = 0
    for payer_code, payer_data in per_payer_code.items():
        processed += 1
        logger.info(f"\n[{processed}/{total_payers}] Processing payer: {payer_code}")
        
        transactions = payer_data.get("transactions", [])

        if not transactions:
            logger.warning(f"  ⚠ No transactions found for {payer_code}")
            results["skipped"].append({
                "payer_code": payer_code,
                "reason": "No transactions"
            })
            continue

        logger.info(f"  Found {len(transactions)} transactions")
        
        # Show total_paid_amount from summary for verification
        summary_total = payer_data.get("total_paid_amount", 0)
        logger.debug(f"  Summary total: {summary_total}")

        # Validate all transactions before processing
        validation_errors = []
        for idx, txn in enumerate(transactions, 1):
            is_valid, error_msg = validate_transaction(txn, payer_code)
            if not is_valid:
                validation_errors.append(error_msg)
                logger.error(f"  ✗ Transaction {idx}: {error_msg}")
        
        if validation_errors:
            logger.error(f"  ✗ Validation failed for {payer_code}")
            results["failed"].append({
                "payer_code": payer_code,
                "errors": validation_errors
            })
            continue

        try:
            # Query for existing wallet
            logger.info(f"  Looking up wallet: reg_no='{payer_code}' (type: {type(payer_code).__name__})")
            
            # Try multiple query methods to debug
            try:
                # Method 1: filter_by
                wallet = TblStudentWallet.query.filter_by(reg_no=payer_code).first()
                logger.info(f"  Query result (filter_by): {wallet}")
                
                # Method 2: Try with explicit string conversion
                if not wallet:
                    wallet = TblStudentWallet.query.filter_by(reg_no=str(payer_code)).first()
                    logger.info(f"  Query result (with str()): {wallet}")
                
                # Method 3: Try direct SQL-like filter
                if not wallet:
                    wallet = TblStudentWallet.query.filter(TblStudentWallet.reg_no == payer_code).first()
                    logger.info(f"  Query result (filter ==): {wallet}")
                
                # Debug: Check if similar values exist
                if not wallet:
                    similar = TblStudentWallet.query.filter(
                        TblStudentWallet.reg_no.like(f'%{payer_code[-4:]}%')
                    ).limit(3).all()
                    if similar:
                        logger.info(f"  Found similar reg_no values: {[w.reg_no for w in similar]}")
                    else:
                        logger.info(f"  No similar reg_no values found")
                        
            except Exception as query_error:
                logger.error(f"  Query error: {query_error}")
                raise

            # Only process if wallet exists
            if not wallet:
                logger.warning(f"  ⚠ Wallet not found for {payer_code} - skipping")
                results["skipped"].append({
                    "payer_code": payer_code,
                    "reason": "Wallet does not exist in database"
                })
                continue

            total_amount = Decimal('0')
            
            logger.info(f"  Found existing wallet (current balance: {wallet.dept})")

            if not dry_run:
                # Reset debt for existing wallet
                wallet.dept = 0
                db.session.flush()

            # Process all transactions
            for idx, txn in enumerate(transactions, 1):
                # Handle large integer transaction references
                transaction_id = str(txn.get("transaction_reference"))
                amount = Decimal(str(txn.get("paid_amount", 0)))
                slip_no = txn.get("slip_no", "")

                logger.debug(f"    [{idx}] Ref: {transaction_id} | Amount: {amount:,.2f} | Slip: {slip_no}")
                
                total_amount += amount

                if not dry_run:
                    # Call topup_wallet
                    TblStudentWallet.topup_wallet(
                        payer_code=payer_code,
                        external_transaction_id=transaction_id,
                        amount=float(amount),
                        slip_no=slip_no if slip_no else None
                    )

            # Update final balance
            if not dry_run:
                wallet.dept = float(total_amount)
                db.session.commit()

            # Verify total matches summary
            summary_total = payer_data.get("total_paid_amount", 0)
            if abs(float(total_amount) - summary_total) > 0.01:
                logger.warning(f"  ⚠ Amount mismatch! Calculated: {total_amount}, Summary: {summary_total}")

            logger.info(f"  ✓ Success: {len(transactions)} txn(s) | Total: {total_amount:,.2f} RWF")

            result_entry = {
                "payer_code": payer_code,
                "total_amount": float(total_amount),
                "transactions": len(transactions)
            }

            results["updated"].append(result_entry)

        except Exception as e:
            if not dry_run:
                db.session.rollback()
            
            logger.error(f"  ✗ Failed: {str(e)}")
            logger.exception("Full traceback:")
            
            results["failed"].append({
                "payer_code": payer_code,
                "error": str(e),
                "error_type": type(e).__name__
            })

    return results


def print_summary(results: dict, logger: logging.Logger):
    """Print a formatted summary of results."""
    logger.info("\n" + "="*60)
    logger.info("IMPORT SUMMARY")
    logger.info("="*60)
    logger.info(f"✓ Created:  {len(results['created']):>4} wallets")
    logger.info(f"✓ Updated:  {len(results['updated']):>4} wallets")
    logger.info(f"✗ Failed:   {len(results['failed']):>4} wallets")
    logger.info(f"⊘ Skipped:  {len(results['skipped']):>4} wallets")
    logger.info("="*60)
    
    # Calculate totals
    total_created = sum(r['total_amount'] for r in results['created'])
    total_updated = sum(r['total_amount'] for r in results['updated'])
    
    logger.info(f"Total amount (created): {total_created:,.2f}")
    logger.info(f"Total amount (updated): {total_updated:,.2f}")
    logger.info(f"Grand total:            {total_created + total_updated:,.2f}")
    logger.info("="*60)
    
    if results['failed']:
        logger.warning(f"\n⚠ {len(results['failed'])} failures detected:")
        for failure in results['failed']:
            logger.warning(f"  - {failure['payer_code']}: {failure.get('error', 'Unknown error')}")


def main():
    """Main entry point."""
    # Parse arguments
    args = sys.argv[1:]
    verbose = "--verbose" in args or "-v" in args
    dry_run = "--dry-run" in args
    
    # Remove flags from args
    args = [a for a in args if not a.startswith("-")]
    
    if len(args) != 1:
        print("Usage:")
        print("  ./wallet_reconciliation_import.py <reconciliation.json> [options]")
        print("\nOptions:")
        print("  --verbose, -v    Enable verbose logging")
        print("  --dry-run        Run without committing to database")
        sys.exit(1)

    json_file = Path(args[0])

    if not json_file.exists():
        print(f"File not found: {json_file}")
        sys.exit(1)

    # Setup logging
    logger = setup_logging(verbose)

    # Create app with context
    app = create_app(os.getenv('FLASK_ENV', 'development'))

    with app.app_context():
        try:
            results = import_wallet_transactions(json_file, logger, dry_run)
            
            # Print summary
            print_summary(results, logger)
            
            # Save detailed results to JSON
            results_file = Path("logs") / f"import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, "w") as f:
                json.dump(results, f, indent=4)
            
            logger.info(f"\nDetailed results saved to: {results_file}")
            
            # Exit with error code if there were failures
            if results['failed']:
                sys.exit(1)
            
        except Exception as e:
            logger.exception("Fatal error occurred")
            sys.exit(1)


if __name__ == "__main__":
    main()