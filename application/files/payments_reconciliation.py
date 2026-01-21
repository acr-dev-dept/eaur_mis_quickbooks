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
    if not txn.get("transaction_reference"):
        return False, f"Missing transaction_reference for {payer_code}"
    
    try:
        amount = float(txn.get("paid_amount", 0))
        if amount <= 0:
            return False, f"Invalid amount {amount} for {payer_code}"
    except (ValueError, TypeError):
        return False, f"Invalid paid_amount format for {payer_code}"
    
    return True, ""


def import_wallet_transactions(json_path: str, logger: logging.Logger, dry_run=False):
    """Import wallet transactions from JSON file."""
    
    logger.info(f"Starting import from: {json_path}")
    logger.info(f"Dry run mode: {dry_run}")
    
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
            wallet = TblStudentWallet.get_by_reg_no(payer_code)

            total_amount = Decimal('0')
            wallet_existed = wallet is not None

            if wallet_existed:
                logger.info(f"  Found existing wallet (current balance: {wallet.dept})")
            else:
                logger.info(f"  Creating new wallet")

            if not dry_run:
                # Create wallet if it doesn't exist
                if not wallet:
                    wallet = TblStudentWallet(
                        reg_no=payer_code,
                        dept=0,
                        is_paid="Yes"
                    )
                    db.session.add(wallet)
                    db.session.flush()
                else:
                    # Reset debt for existing wallet
                    wallet.dept = 0
                    db.session.flush()

            # Process all transactions
            for idx, txn in enumerate(transactions, 1):
                transaction_id = str(txn.get("transaction_reference"))
                amount = Decimal(str(txn.get("paid_amount", 0)))
                slip_no = txn.get("slip_no", "N/A")

                logger.debug(f"    Transaction {idx}: {transaction_id} | Amount: {amount} | Slip: {slip_no}")
                
                total_amount += amount

                if not dry_run:
                    # Call topup_wallet
                    TblStudentWallet.topup_wallet(
                        payer_code=payer_code,
                        external_transaction_id=transaction_id,
                        amount=float(amount),
                        slip_no=txn.get("slip_no")
                    )

            # Update final balance
            if not dry_run:
                wallet.dept = float(total_amount)
                db.session.commit()

            logger.info(f"  ✓ Success: {len(transactions)} transactions | Total: {total_amount}")

            result_entry = {
                "payer_code": payer_code,
                "total_amount": float(total_amount),
                "transactions": len(transactions)
            }

            if wallet_existed:
                results["updated"].append(result_entry)
            else:
                results["created"].append(result_entry)

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