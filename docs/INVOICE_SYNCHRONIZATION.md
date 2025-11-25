# Invoice Synchronization Guide

## Overview

The EAUR MIS-QuickBooks Integration includes a comprehensive invoice synchronization system that automates the transfer of existing invoices from the MIS database to QuickBooks Online. This system ensures data consistency, provides progress tracking, and handles errors gracefully.

## Features

### ==YES==**Comprehensive Synchronization**
- **Bulk Processing**: Synchronize thousands of invoices efficiently
- **Batch Processing**: Process invoices in configurable batches to avoid API rate limits
- **Progress Tracking**: Real-time monitoring of synchronization progress
- **Error Handling**: Robust error handling with retry mechanisms

### ==YES==**Data Integrity**
- **Status Tracking**: Track synchronization status for each invoice
- **Audit Logging**: Complete audit trail of all synchronization activities
- **Data Validation**: Validate data before sending to QuickBooks
- **Duplicate Prevention**: Prevent duplicate synchronization

### ==YES==**Flexible Management**
- **API Endpoints**: RESTful API for programmatic control
- **Command Line Tools**: CLI tools for manual management
- **Multiple Sync Options**: Single invoice, batch, or full synchronization

## Architecture

### Database Schema

The synchronization system uses the existing MIS invoice table with additional tracking fields:

```sql
-- MIS Invoice Table (tbl_imvoice)
QuickBk_Status    INT DEFAULT 0    -- 0=not synced, 1=synced, 2=failed, 3=in progress
pushed_by         VARCHAR(200)     -- User/service that performed sync
pushed_date       DATETIME         -- When sync was performed
```

### Service Layer

**InvoiceSyncService** (`application/services/invoice_sync.py`)
- Core synchronization logic
- Data mapping and transformation
- Batch processing management
- Error handling and recovery

### API Layer

**Sync API** (`application/api/v1/sync.py`)
- RESTful endpoints for synchronization control
- Progress monitoring and statistics
- Error reporting and status updates

## Usage Guide

### 1. Prerequisites

Before starting synchronization, ensure:

1. **QuickBooks Authentication**: QuickBooks must be connected and authenticated
2. **Database Access**: MIS database connection is configured
3. **Environment Setup**: All dependencies are installed

```bash
# Check QuickBooks connection status
curl http://localhost:5000/api/v1/sync/status
```

### 2. Analysis Phase

First, analyze your synchronization requirements:

#### Via API:
```bash
curl http://localhost:5000/api/v1/sync/analyze
```

#### Via Command Line:
```bash
python3 tools/sync_invoices.py analyze
```

**Sample Output:**
```
📊 Synchronization Statistics:
   Total Invoices: 1,250
   ==YES==Already Synced: 0
   ⏳ Not Synced: 1,250
   ❌ Failed: 0
   🔄 In Progress: 0
   📈 Progress: 0.0%
```

### 3. Preview Phase

Preview invoices that will be synchronized:

#### Via API:
```bash
curl "http://localhost:5000/api/v1/sync/preview?limit=10"
```

#### Via Command Line:
```bash
python3 tools/sync_invoices.py preview --limit 10
```

### 4. Synchronization Options

#### Option A: Batch Synchronization (Recommended)

Process invoices in manageable batches:

**API:**
```bash
curl -X POST http://localhost:5000/api/v1/sync/batch \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50}'
```

**Command Line:**
```bash
python3 tools/sync_invoices.py batch --batch-size 50
```

#### Option B: Full Synchronization

Synchronize all invoices at once:

**API:**
```bash
curl -X POST http://localhost:5000/api/v1/sync/all \
  -H "Content-Type: application/json" \
  -d '{"max_batches": 10}'
```

**Command Line:**
```bash
python3 tools/sync_invoices.py all --max-batches 10
```

#### Option C: Single Invoice Synchronization

Synchronize a specific invoice:

**API:**
```bash
curl -X POST http://localhost:5000/api/v1/sync/single/12345
```

### 5. Monitoring Progress

Monitor synchronization progress in real-time:

#### Via API:
```bash
curl http://localhost:5000/api/v1/sync/status
```

#### Via Command Line:
```bash
python3 tools/sync_invoices.py status
```

## API Reference

### GET /api/v1/sync/analyze
Analyze synchronization requirements and return statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_invoices": 1250,
    "not_synced": 1250,
    "already_synced": 0,
    "failed": 0,
    "in_progress": 0
  },
  "message": "Synchronization analysis completed successfully"
}
```

### GET /api/v1/sync/preview
Preview unsynchronized invoices.

**Parameters:**
- `limit` (optional): Number of invoices to return (default: 10, max: 100)
- `offset` (optional): Number of invoices to skip (default: 0)

### POST /api/v1/sync/batch
Synchronize a batch of invoices.

**Request Body:**
```json
{
  "batch_size": 50
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_processed": 50,
    "successful": 48,
    "failed": 2,
    "errors": [
      {
        "invoice_id": 123,
        "error": "Customer not found"
      }
    ]
  }
}
```

### POST /api/v1/sync/all
Synchronize all unsynchronized invoices.

**Request Body:**
```json
{
  "max_batches": 10
}
```

### POST /api/v1/sync/single/{invoice_id}
Synchronize a single invoice by ID.

### GET /api/v1/sync/status
Get current synchronization status and statistics.

## Data Mapping

The synchronization system maps MIS invoice data to QuickBooks format:

### MIS Invoice → QuickBooks Invoice

| MIS Field | QuickBooks Field | Notes |
|-----------|------------------|-------|
| `id` | `DocNumber` | Prefixed with "MIS-" |
| `reg_no` | `CustomerRef.name` | Student registration number |
| `dept` | `Line.Amount` | Debit amount |
| `invoice_date` | `TxnDate` | Invoice date |
| `comment` | `PrivateNote` | Internal notes |
| `fee_category` | `Line.Description` | Fee category description |

### Customer Mapping

Students are automatically created as customers in QuickBooks:
- **Name**: Student full name (from `tbl_personal_ug`)
- **Display Name**: Registration number
- **Contact Info**: Email and phone (if available)

## Error Handling

### Common Errors and Solutions

1. **"Customer not found"**
   - **Cause**: Student record missing in MIS
   - **Solution**: Verify student data in `tbl_personal_ug`

2. **"Invalid amount"**
   - **Cause**: Zero or negative invoice amount
   - **Solution**: Check `dept` and `credit` fields

3. **"QuickBooks API rate limit"**
   - **Cause**: Too many API requests
   - **Solution**: Reduce batch size or add delays

4. **"Authentication failed"**
   - **Cause**: QuickBooks tokens expired
   - **Solution**: Re-authenticate with QuickBooks

### Retry Mechanism

Failed invoices are automatically retried:
- **Max Retries**: 3 attempts
- **Retry Delay**: 5 seconds between attempts
- **Status Tracking**: Failed invoices marked with status `2`

## Best Practices

### 1. **Start Small**
Begin with small batches (10-20 invoices) to test the process.

### 2. **Monitor Progress**
Regularly check synchronization status and address errors promptly.

### 3. **Schedule Wisely**
Run large synchronizations during off-peak hours to minimize impact.

### 4. **Backup Data**
Always backup your QuickBooks data before large synchronizations.

### 5. **Validate Results**
Verify synchronized data in QuickBooks after completion.

## Troubleshooting

### Issue: Synchronization Stuck
**Symptoms**: Invoices remain in "in progress" status
**Solution**: 
```bash
# Reset stuck invoices
python3 tools/sync_invoices.py analyze
# Check for specific errors in logs
```

### Issue: High Failure Rate
**Symptoms**: Many invoices failing to sync
**Solution**:
1. Check QuickBooks connection
2. Verify student data completeness
3. Review error messages in audit logs

### Issue: Performance Problems
**Symptoms**: Slow synchronization
**Solution**:
1. Reduce batch size
2. Check network connectivity
3. Monitor QuickBooks API rate limits

## Support

For technical support:
- **Email**: support@acr-online.rw
- **Documentation**: Check application logs in `logs/app.log`
- **API Errors**: Review QuickBooks audit logs in database
