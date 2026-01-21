#!/usr/bin/env python3
"""
Wallet reconciliation CLI importer - Updated with proper MIS session management

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
from datetime import datetime
import argparse

# Adjust BASE_DIR if needed
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from application import create_app
from application.utils.database import db_manager              # ← your DatabaseManager
from application.models.mis_models import TblStudentWallet


def setup_logging(verbose=False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"wallet_import_{timestamp}.log"
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s | %(levelname)-7s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Log file created: {log_file}")
    return logger


def validate_transaction(txn: dict, payer_code: str) -> tuple[bool, str]:
    """Validate a single transaction record."""
    txn_ref = txn.get("transaction_reference")
    if txn_ref is None or str(txn_ref).strip() == "":
        return False, "Missing transaction_reference"
    
    try:
        amount = float(txn.get("paid_amount", 0))
        if amount <= 0:
            return False, f"Invalid amount: {amount}"
    except (ValueError, TypeError):
        return False, f"Invalid paid_amount format: {txn.get('paid_amount')}"
    
    slip_no = txn.get("slip_no")
    if slip_no is not None and not isinstance(slip_no, str):
        return False, f"slip_no must be string, got {type(slip_no).__name__}"
    
    return True, ""


def import_wallet_transactions(json_path: Path, logger: logging.Logger, dry_run: bool = False):
    """Import wallet transactions from JSON file using MIS session."""
    
    logger.info(f"Starting import from: {json_path}")
    logger.info(f"Dry run: {dry_run}")

    # Quick DB health check
    try:
        with db_manager.get_mis_session() as session:
            wallet_count = session.query(TblStudentWallet).count()
            logger.info(f"Database connected - found {wallet_count} wallets")
            
            # Sample reg_no for debugging
            samples = session.query(TblStudentWallet.reg_no).limit(5).all()
            logger.info(f"Sample reg_no: {[r[0] for r in samples]}")
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    per_payer_code = data.get("per_payer_code", {})
    total_payers = len(per_payer_code)
    logger.info(f"Found {total_payers} payer codes to process")

    results = {
        "updated": 0,
        "failed": 0,
        "skipped": 0,
        "details": []
    }

    processed = 0

    for payer_code, payer_data in per_payer_code.items():
        processed += 1
        logger.info(f"[{processed}/{total_payers}] Processing payer: {payer_code}")

        transactions = payer_data.get("transactions", [])
        if not transactions:
            logger.warning(f"  No transactions → skipping")
            results["skipped"] += 1
            continue

        logger.info(f"  {len(transactions)} transactions found")

        # Validate all first
        validation_errors = []
        for idx, txn in enumerate(transactions, 1):
            valid, msg = validate_transaction(txn, payer_code)
            if not valid:
                validation_errors.append(f"Txn {idx}: {msg}")

        if validation_errors:
            logger.error(f"  Validation failed:\n" + "\n".join(validation_errors))
            results["failed"] += 1
            results["details"].append({"payer_code": payer_code, "status": "validation_failed"})
            continue

        try:
            with db_manager.get_mis_session() as session:
                # Lookup wallet using current session
                wallet = session.query(TblStudentWallet).filter_by(reg_no=payer_code).first()

                if not wallet:
                    logger.warning(f"  Wallet not found for reg_no='{payer_code}' → skipping")
                    results["skipped"] += 1
                    results["details"].append({"payer_code": payer_code, "status": "wallet_not_found"})
                    continue

                logger.info(f"  Found wallet - current dept/balance: {wallet.dept}")

                total_amount = Decimal('0')

                # Reset dept before applying payments
                wallet.dept = 0
                session.flush()

                # Apply each transaction
                for idx, txn in enumerate(transactions, 1):
                    transaction_id = str(txn.get("transaction_reference"))
                    amount = Decimal(str(txn.get("paid_amount", 0)))
                    slip_no = txn.get("slip_no") or None

                    logger.debug(f"    Txn {idx} | Ref: {transaction_id} | Amt: {amount:,.2f} | Slip: {slip_no}")

                    total_amount += amount

                    if not dry_run:
                        TblStudentWallet.topup_wallet(
                            payer_code=payer_code,
                            external_transaction_id=transaction_id,
                            amount=float(amount),
                            slip_no=slip_no,
                            session=session   # ← pass session if topup_wallet supports it
                        )

                # Final balance update
                if not dry_run:
                    wallet.dept = float(total_amount)
                    session.commit()

                logger.info(f"  ✓ Processed successfully | Total: {total_amount:,.2f}")

                results["updated"] += 1
                results["details"].append({
                    "payer_code": payer_code,
                    "status": "success",
                    "transactions": len(transactions),
                    "total_amount": float(total_amount)
                })

        except Exception as e:
            logger.error(f"  Processing failed for {payer_code}: {e}", exc_info=True)
            results["failed"] += 1
            results["details"].append({
                "payer_code": payer_code,
                "status": "error",
                "error": str(e)
            })
            # session rolls back automatically via context manager

    return results


def print_summary(results: dict, logger: logging.Logger):
    logger.info("\n" + "═" * 60)
    logger.info("WALLET IMPORT SUMMARY")
    logger.info("═" * 60)
    logger.info(f"✓ Updated:  {results['updated']}")
    logger.info(f"✗ Failed:   {results['failed']}")
    logger.info(f"⊘ Skipped:  {results['skipped']}")
    logger.info("═" * 60)

    if results["details"]:
        logger.info("Details:")
        for d in results["details"]:
            logger.info(f"  {d['payer_code']} → {d['status']}")


def main():
    parser = argparse.ArgumentParser(description="Import wallet reconciliation from JSON")
    parser.add_argument("file", help="Path to reconciliation JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without DB changes")

    args = parser.parse_args()

    logger = setup_logging(verbose=args.verbose)

    json_path = Path(args.file)
    if not json_path.is_file():
        logger.error(f"File not found: {json_path}")
        sys.exit(1)

    # Minimal app context (needed for some extensions/models)
    app = create_app('development')  # adjust env if needed

    with app.app_context():
        try:
            results = import_wallet_transactions(json_path, logger, dry_run=args.dry_run)
            print_summary(results, logger)

            if results["failed"] > 0:
                logger.warning(f"Finished with {results['failed']} failures")
                sys.exit(1)
            else:
                logger.info("Import completed successfully")
                sys.exit(0)

        except Exception as e:
            logger.exception("Fatal error during import")
            sys.exit(1)


if __name__ == "__main__":
    main()